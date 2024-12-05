from fastapi import FastAPI
import requests
import json
import csv
import time
import logging
import asyncio
from kafka import KafkaProducer, KafkaConsumer
from textblob import TextBlob

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_TOPIC = 'trading_signals'
KAFKA_BROKER = '127.0.0.1:9092'
NEWS_API_KEY = '9ebfc0cfe4b240c69f562e3d6d0d8843'
CATEGORIES = ['Tech', 'Construction', 'Petroleum', 'Finance', 'Health']

app = FastAPI()


async def fetch_news():
    """Fetch news data from the NewsAPI asynchronously."""
    url = f'https://newsapi.org/v2/everything?q=stock market&apiKey={NEWS_API_KEY}'
    response = await asyncio.to_thread(requests.get, url)
    return response.json().get('articles', [])


async def analyze_sentiment(text):
    """Analyze sentiment using TextBlob asynchronously."""
    analysis = await asyncio.to_thread(TextBlob, text)
    return analysis.sentiment.polarity


def generate_signal(polarity):
    """Generate a buy/sell/hold signal based on sentiment polarity."""
    if polarity >= 0.5:
        return 'BUY'
    elif polarity <= -0.5:
        return 'SELL'
    else:
        return 'HOLD'


async def stream_to_kafka(news_data):
    """Stream the news data to Kafka asynchronously."""
    producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER,
                             value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    for article in news_data:
        title = article['title']
        url = article['url']
        sentiment = await analyze_sentiment(title)
        signal = generate_signal(sentiment)

        message = {'title': title, 'url': url, 'sentiment': sentiment, 'signal': signal}
        producer.send(KAFKA_TOPIC, value=message)

    producer.close()
    logger.info("News data streamed to Kafka.")


async def consume_from_kafka():
    """Consume news data from Kafka asynchronously."""
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        session_timeout_ms=160000,
        request_timeout_ms=170000
    )
    news_records = []
    logger.info(f"Consumer started, waiting for messages on topic: {KAFKA_TOPIC}...")

    def consume_messages():
        for message in consumer:
            record = json.loads(message.value.decode('utf-8'))
            news_records.append(record)

            logger.info(f"Consumed message: {record['title']} - {record['url']}")
            if len(news_records) >= 10:
                break

            time.sleep(1)
        consumer.close()
        logger.info(f"Data consumed from Kafka. Total records: {len(news_records)}.")

    await asyncio.to_thread(consume_messages)
    return news_records

async def save_to_csv(news_records):
    """Save the consumed news data to a CSV file asynchronously."""
    csv_file = 'news_data.csv'

    def write_to_csv():
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Title', 'URL', 'Sentiment', 'Signal'])
            for record in news_records:
                writer.writerow([record['title'], record['url'], record['sentiment'], record['signal']])
        logger.info(f"Data saved to {csv_file}.")

    await asyncio.to_thread(write_to_csv)
    return csv_file



