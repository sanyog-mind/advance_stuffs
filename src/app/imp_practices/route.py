from sqlalchemy.orm import joinedload
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from src.app.imp_practices.service import get_employees_and_projects, get_employees_without_task, get_aggregate_hours, \
    get_aggregate_hours_project_wise, get_top_contributor, get_department_task_completion_status, get_top_performers, \
    get_project_wise_summary
from src.connection.connection import ConnectionHandler, get_connection_handler_for_app

main_router = APIRouter()

@main_router.get("/departments/{department_id}/employees")
async def get_employees_in_department(department_id: int,
                                connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
                                ):
    session = connection_handler.session

    data = await get_employees_and_projects(department_id, session)

    if not data:
        raise HTTPException(status_code=404, detail="Department not found")

    return JSONResponse(content=data)

@main_router.get("/employees")
async def get_employees_without_task_route(
                                connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
                                ):
    session = connection_handler.session

    data = await get_employees_without_task(session)

    if not data:
        raise HTTPException(status_code=404, detail="Department not found")

    return JSONResponse(content=data)

@main_router.get("/get_aggregate_hours")
async def aggregate_project_hours(
                                connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
                                ):
    session = connection_handler.session

    data = await get_aggregate_hours(session)

    if not data:
        raise HTTPException(status_code=404, detail="Department not found")

    return JSONResponse(content=data)

@main_router.get("/get_aggregate_hours_project_wise/{project_id}")
async def aggregate_project_hours(project_id:int,
                                connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
                                ):
    session = connection_handler.session

    data = await get_aggregate_hours_project_wise(project_id,session)

    if not data:
        raise HTTPException(status_code=404, detail="Department not found")

    return (JSONResponse(content=data))

@main_router.get("/get_top_contributor/{project_id}")
async def get_top_contributor_route(project_id:int,
                                connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app),
                                ):
    session = connection_handler.session

    data = await get_top_contributor(project_id,session)

    if not data:
        raise HTTPException(status_code=404, detail="Department not found")

    return JSONResponse(content=data)


@main_router.get("/departments/{department_id}/task-completion-status")
async def get_department_task_completion_route(
        department_id: int,
        connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app)
):

    session = connection_handler.session

    try:
        data = await get_department_task_completion_status(department_id, session)

        if isinstance(data, dict) and "message" in data:
            raise HTTPException(status_code=404, detail=data["message"])

        return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@main_router.get("/employees/top-performers")
async def get_top_performers_route(
        connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app)
):
    """
    Endpoint to retrieve top 3 performing employees.

    Args:
        connection_handler (ConnectionHandler): Database connection handler

    Returns:
        JSONResponse with top performers or error message
    """
    session = connection_handler.session

    try:
        data = await get_top_performers(session)

        if isinstance(data, dict) and "message" in data:
            raise HTTPException(status_code=404, detail=data["message"])

        return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@main_router.get("/projects/{project_id}/timesheet-summary")
async def get_project_timesheet_summary_route(
        project_id: int,
        connection_handler: ConnectionHandler = Depends(get_connection_handler_for_app)
):
    """
    Endpoint to retrieve timesheet summary for a specific project.

    Args:
        project_id (int): ID of the project
        connection_handler (ConnectionHandler): Database connection handler

    Returns:
        JSONResponse with project timesheet summary or error message
    """
    session = connection_handler.session

    try:
        data = await get_project_wise_summary(project_id, session)

        if isinstance(data, dict) and "message" in data:
            raise HTTPException(status_code=404, detail=data["message"])

        return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))