from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, func, desc, case
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
        or_(Task.assigned_to == None, Task.assigned_to != Employee.id)
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

# 1. Get Task Completion Status by Department
#
# Endpoint: /departments/{department_id}/task-completion-status
# Description: Fetch the total number of tasks, completed tasks, and pending tasks for each project in a department.

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
    # Subquery to calculate total hours worked and completed tasks for each employee
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
            Employee.first_name,
            Employee.last_name,
            Department.name
        )
        .order_by(
            func.count(Task.id).desc(),  # Primary sort by completed tasks
            func.sum(Timesheet.hours_worked).desc()  # Secondary sort by total hours
        )
        .limit(3)
    )

    # Execute the query
    result = await db.execute(query)
    top_performers = result.all()

    # If no top performers found
    if not top_performers:
        return {"message": "No top performers found"}

    # Format the results
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