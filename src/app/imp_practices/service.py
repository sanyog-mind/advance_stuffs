from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, func, desc, case, distinct
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.imp_practices.models import Department, Employee, Project, Task, Timesheet


async def get_employees_and_projects(department_id: int, db: AsyncSession):
    department_query = (
        select(Department)
        .options(selectinload(Department.employees))
        .filter(Department.id == department_id)
    )
    department = await db.execute(department_query)
    department = department.scalar_one_or_none()

    print("department", department.employees)
    if not department:
        return None

    data = []
    for employee in department.employees:

        projects_query = (
            select(Project)
            .join(Task)
            .options(selectinload(Project.tasks))
            .filter(Task.assigned_to == employee.id)
        )
        projects_result = await db.execute(projects_query)
        projects = projects_result.scalars().unique().all()

        data.append({
            "employee_name": f"{employee.first_name} {employee.last_name}",
            "projects": [
                {
                    "project_name": project.name,
                    "tasks": [{"task_name": t.name} for t in project.tasks]
                }
                for project in projects
            ]
        })

    return {"department": department.name, "employees": data}


async def get_employees_without_task( db: AsyncSession):

    employees_query = (select(Employee).outerjoin(Task)
    .filter(
        or_(Task.assigned_to == None, Task.assigned_to == Employee.id)
    )
    )
    result = await db.execute(employees_query)
    employee = result.scalars().all()

    return [
        {
            "id": emp.id,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "email": emp.email,
            "department_id": emp.department_id
        } for emp in employee
    ]

async def get_aggregate_hours( db: AsyncSession):

    query = (
        select(Project.name, func.sum(Timesheet.hours_worked).label('total_hours'))
        .join(Task, Task.project_id == Project.id)
        .join(Timesheet, Timesheet.task_id == Task.id)
        .group_by(Project.name)
    )

    result = await db.execute(query)

    projects = result.all()
    return [{"project_name": project.name, "total_hours": project.total_hours} for project in projects]

async def get_aggregate_hours_project_wise(project_id:int, db: AsyncSession):
    query = (
        select(Project.name,func.sum(Timesheet.hours_worked).label('total_hours')).
                   join(Task,Task.project_id == Project.id).
                   join(Timesheet,Timesheet.task_id == Task.id).
                    filter(Project.id == project_id).
                   group_by(Project.name)
             )

    result = await db.execute(query)

    projects = result.all()
    return [{"project_name": project.name, "total_hours": project.total_hours} for project in projects]

async def get_top_contributor(project_id, db: AsyncSession):
    query = (
        select(Employee.first_name,func.sum(Timesheet.hours_worked).label('total_hours')).
        join(Task,Task.assigned_to == Employee.id).
        join(Timesheet,Timesheet.task_id == Task.id).
        filter(Task.project_id == project_id).
        group_by(Employee.id)
        .order_by(desc(func.sum(Timesheet.hours_worked)))
    )

    result = await db.execute(query)
    top_contributor = result.first()

    if not top_contributor:
        return {"message": "No contributors found for the specified project"}

    employee_id, total_hours = top_contributor
    top_contributor_data = {
        "employee_name": employee_id,
        "hours": f"{total_hours}"
    }

    return jsonable_encoder(top_contributor_data)

async def get_department_task_completion_status(department_id: int, db: AsyncSession):
    """
    Retrieve task completion status for all projects within a specific department.

    Args:
        department_id (int): ID of the department to analyze
        db (AsyncSession): Database session

    Returns:
        Dict containing project-level task completion statistics
    """
    query = (
        select(Project)
        .join(Task, Project.id == Task.project_id)
        .join(Employee, Task.assigned_to == Employee.id)
        .filter(Employee.department_id == department_id)
        .options(joinedload(Project.tasks))
        .distinct()
    )

    result = await db.execute(query)
    projects = result.scalars().unique().all()

    if not projects:
        return {"message": "No projects found for the specified department"}

    project_task_stats = []
    for project in projects:
        total_tasks = len(project.tasks)

        completed_tasks = sum(1 for task in project.tasks if task.status == 'Completed')
        pending_tasks = sum(1 for task in project.tasks if task.status == 'Pending')
        in_progress_tasks = sum(1 for task in project.tasks if task.status == 'In Progress')

        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        project_task_stats.append({
            "project_id": project.id,
            "project_name": project.name,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completion_percentage": round(completion_percentage, 2)
        })

    return jsonable_encoder(project_task_stats)


async def get_top_performers(db: AsyncSession):
    """
    Retrieve top 3 employees based on completed tasks and total hours worked.

    Args:
        db (AsyncSession): Database session

    Returns:
        List of top performers with their details
    """
    query = (
        select(
            Employee.id.label('employee_id'),
            Employee.first_name,
            Employee.last_name,
            Department.name.label('department_name'),
            func.count(Task.id).label('completed_tasks'),
            func.sum(Timesheet.hours_worked).label('total_hours')
        )
        .join(Department, Employee.department_id == Department.id)
        .join(Task, Employee.id == Task.assigned_to)
        .join(Timesheet, Timesheet.task_id == Task.id)
        .filter(Task.status == 'Completed')
        .group_by(
            Employee.id,
            Department.name
        )
        .order_by(
            func.count(Task.id).desc(),
            func.sum(Timesheet.hours_worked).desc()
        )
        .limit(3)
    )

    result = await db.execute(query)
    top_performers = result.all()

    if not top_performers:
        return {"message": "No top performers found"}

    formatted_performers = []
    for performer in top_performers:
        formatted_performers.append({
            "employee_id": performer.employee_id,
            "name": f"{performer.first_name} {performer.last_name}",
            "department": performer.department_name,
            "completed_tasks": performer.completed_tasks,
            "total_hours_worked": round(performer.total_hours or 0, 2)
        })

    return jsonable_encoder(formatted_performers)


async def get_project_wise_summary(project_id: int, db: AsyncSession):
    """
    Retrieve a detailed timesheet summary for a specific project.
    Args:
        project_id (int): ID of the project to retrieve summary for
        db (AsyncSession): Database session
    Returns:
        List of employee timesheet summaries for the project
    """
    total_project_hours_subquery = (
        select(func.sum(Timesheet.hours_worked).label('total_project_hours'))
        .join(Task, Timesheet.task_id == Task.id)
        .filter(Task.project_id == project_id)
        .scalar_subquery()
    )
    #
    total_employee_in_project= (
        select(
            func.count(distinct(Employee.id)).label('total_employees'))
            .select_from(Employee).
            join(Task).
            filter(Task.project_id==project_id)

    )

    query = (
        select(
            Project.name.label('project_name'),
            total_project_hours_subquery.label('total_project_hours'),
            total_employee_in_project.label('total_employee_in_project'),
            Employee.id.label('employee_id'),
            Employee.first_name,
            Employee.last_name,
            Department.name.label('department_name'),
            func.count(distinct(Task.id)).label('total_tasks'),
            func.sum(Timesheet.hours_worked).label('total_hours'),
            func.count(case((Task.status == 'Completed', 1))).label('completed_tasks'),

        )
        .select_from(Project)
        .join(Task, Task.project_id == Project.id)
        .join(Employee, Task.assigned_to == Employee.id)
        .join(Department, Employee.department_id == Department.id)
        .join(Timesheet, Timesheet.task_id == Task.id)
        .filter(Task.project_id == project_id)
        .group_by(
            Project.name,
            Employee.id,
            Employee.first_name,
            Employee.last_name,
            Department.name
        )
        .order_by(func.sum(Timesheet.hours_worked).desc())
    )

    result = await db.execute(query)
    project_summaries = result.all()

    project_query = select(Project).filter(Project.id == project_id)
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        return {"message": f"Project with ID {project_id} not found"}

    # If no timesheets found
    if not project_summaries:
        return {"message": "No timesheet entries found for this project"}

    # Format the results
    formatted_summaries = []
    for summary in project_summaries:
        formatted_summaries.append({
            "total_emp":summary.total_employee_in_project,
            "project_name": summary.project_name,
            "total_project_hours":summary.total_project_hours,
            "employee_id": summary.employee_id,
            "name": f"{summary.first_name} {summary.last_name}",
            "department": summary.department_name,
            "total_tasks": summary.total_tasks,
            "completed_tasks": summary.completed_tasks,
            "total_hours_worked": round(summary.total_hours or 0, 2)
        })

    return jsonable_encoder(formatted_summaries)