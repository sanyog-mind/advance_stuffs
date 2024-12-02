from fastapi import APIRouter
from fastapi.responses import FileResponse
from src.app.stream_data.service import fetch_news, stream_to_kafka, consume_from_kafka, save_to_csv

stream_router = APIRouter()

@stream_router.post("/fetch_and_stream")
async def fetch_and_stream():
    """Fetch news and stream to Kafka."""
    news_data = await fetch_news()
    await stream_to_kafka(news_data)
    return {"message": "News data fetched and streamed to Kafka successfully."}


@stream_router.post("/consume_and_save")
async def consume_and_save():
    """Consume data from Kafka, save to CSV, and return the CSV as response."""
    news_records = await consume_from_kafka()
    csv_file = await save_to_csv(news_records)
    return FileResponse(csv_file, media_type="text/csv")