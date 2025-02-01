import sqlite3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime

###working with amazon db###
conn = sqlite3.connect(
    "C://Users//apatu//PycharmProjects//PythonProject//amazon_reviews.db")
cursor = conn.cursor()

cursor.execute("SELECT SID, message FROM reviews")
rows = cursor.fetchall()

analyzer = SentimentIntensityAnalyzer()

for sid, message in rows:
    sentiment_scores = analyzer.polarity_scores(message)
    compound_score = sentiment_scores['compound']
    pos_score = sentiment_scores['pos']
    neg_score = sentiment_scores['neg']
    neu_score = sentiment_scores['neu']

    if compound_score > 0.7 and pos_score > 0.3:
        sentiment = 'Strong Positive'
    elif compound_score > 0.2 and pos_score > neg_score:
        sentiment = 'Positive'
    elif -0.2 <= compound_score <= 0.2 and neu_score >= 0.6:
        sentiment = 'Neutral'
    elif -0.5 < compound_score < -0.2 and neg_score > pos_score:
        sentiment = 'Negative'
    else:
        sentiment = 'Strong Negative'

    cursor.execute("UPDATE reviews SET sentiment = ? WHERE SID = ?", (sentiment, sid))


#converting date format for db amazon
cursor.execute("PRAGMA table_info(reviews)")
columns = [column[1] for column in cursor.fetchall()]

if 'DateConverted' not in columns:
    cursor.execute("ALTER TABLE reviews ADD COLUMN dateconverted DATE")
else:
    print("Column 'DateConverted' already exists.")

cursor.execute("SELECT SID, Date FROM reviews")
rows = cursor.fetchall()

for row in rows:
    SID, Date = row
    if Date:
        parts = Date.split()
        month = parts[0]
        day = parts[1].replace(',', '')
        year = parts[2]
        month_number = {
            "January": "01", "February": "02", "March": "03", "April": "04",
            "May": "05", "June": "06", "July": "07", "August": "08",
            "September": "09", "October": "10", "November": "11", "December": "12"
        }[month]
        new_date = f"{year}-{month_number}-{day.zfill(2)}"

        cursor.execute("UPDATE reviews SET dateconverted = ? WHERE SID = ?", (new_date, SID))

conn.commit()
conn.close()





###working with sentiment db###
conn = sqlite3.connect(
    "C://Users//apatu//PycharmProjects//PythonProject//sentiment.db")

cursor = conn.cursor()

cursor.execute("SELECT SID, Message FROM data")
rows = cursor.fetchall()

analyzer = SentimentIntensityAnalyzer()

for sid, message in rows:
    sentiment_scores = analyzer.polarity_scores(message)
    compound_score = sentiment_scores['compound']
    pos_score = sentiment_scores['pos']
    neg_score = sentiment_scores['neg']
    neu_score = sentiment_scores['neu']

    if compound_score > 0.7 and pos_score > 0.3:
        sentiment = 'Strong Positive'
    elif compound_score > 0.2 and pos_score > neg_score:
        sentiment = 'Positive'
    elif -0.2 <= compound_score <= 0.2 and neu_score >= 0.6:
        sentiment = 'Neutral'
    elif -0.5 < compound_score < -0.2 and neg_score > pos_score:
        sentiment = 'Negative'
    else:
        sentiment = 'Strong Negative'

    cursor.execute("UPDATE data SET Sentiment = ? WHERE SID = ?", (sentiment, sid))



table_name = "data"
converted_column = "dateconverted"
id_column = "SID"

try:
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {converted_column} DATE")
except sqlite3.OperationalError:
    print(f"Column '{converted_column}' already exists.")

cursor.execute(f"SELECT * FROM {table_name}")
rows = cursor.fetchall()

def convert_date_format(date_str):
    try:
        parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return parsed_date.strftime("%Y-%m-%d")  # Формат: YYYY-MM-DD
    except ValueError:
        return None

for row in rows:
    row_id = row[0]
    original_date = row[3]
    converted_date = convert_date_format(original_date)

    if converted_date:
        cursor.execute(
            f"UPDATE {table_name} SET {converted_column} = ? WHERE {id_column} = ?",
            (converted_date, row_id)
        )

conn.commit()
conn.close()