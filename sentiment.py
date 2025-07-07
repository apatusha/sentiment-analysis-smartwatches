import sqlite3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from mastodon import Mastodon
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
import pandas as pd


# Sentiment Analysis Setup
analyzer = SentimentIntensityAnalyzer()

# Function to analyze sentiment
def analyze_sentiment(messages):
    results = []
    for sid, message in messages:
        scores = analyzer.polarity_scores(message)
        compound = scores['compound']
        pos = scores['pos']
        neg = scores['neg']
        neu = scores['neu']
        sentiment = ('Strong Positive' if compound > 0.7 and pos > 0.3 else
                     'Positive' if compound > 0.2 and pos > neg else
                     'Neutral' if -0.2 <= compound <= 0.2 and neu >= 0.6 else
                     'Negative' if -0.5 < compound < -0.2 and neg > pos else
                     'Strong Negative')
        results.append((sentiment, sid))
    return results

# Function to clean messages
def clean_message(message):
    soup = BeautifulSoup(message, 'html.parser')
    text = soup.get_text()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Function to extract date from raw date string
def extract_date(raw_date):
    if "on" in raw_date:
        date_part = raw_date.split("on")[1].strip()
    else:
        date_part = raw_date.strip()
    return date_part

# Initialize Mastodon API
mastodon = Mastodon(
    access_token="gT9H9Q6JexEx0FtGgt53tWBQR60Z3RqvZmQAYf2qJm4",
    api_base_url="https://mastodon.social"
)

# Load search terms
with open('terms.json', 'r') as file:
    data = json.load(file)
    search_terms = data['terms']

# Connect to SQLite Database
conn = sqlite3.connect("sentiment.db")
cursor = conn.cursor()

# Create Tables If Not Exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS reviews (
               SID INTEGER PRIMARY KEY AUTOINCREMENT,
               Product TEXT,
               User TEXT,
               Date TEXT,
               Message TEXT,
               Sentiment TEXT DEFAULT '',
               Dateconverted DATE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS data (
               SID INTEGER PRIMARY KEY AUTOINCREMENT,
               Product TEXT,
               User TEXT,
               Date TEXT,
               Message TEXT,
               Sentiment TEXT,
               Dateconverted DATE
)
''')

conn.commit()

# Scrape Mastodon Data
for term in search_terms:
    print(f"Searching for {term}")
    results = mastodon.timeline_hashtag(term, limit=50)
    if not results:
        print(f"No results found for {term}")
        continue
    for status in results:
        user = status['account']['username']
        date = status["created_at"]
        raw_message = status['content']
        message = clean_message(raw_message)
        if not message:
            print("Empty message, skipping...")
            continue
        cursor.execute('''
        INSERT INTO data (Product, User, Date, Message, Sentiment)
        VALUES (?, ?, ?, ?, ?)
        ''', (term, user, date, message, None))
conn.commit()

# Scrape Amazon Reviews
product_data = []
with open('terms.txt', 'r') as file:
    for line in file:
        line = line.strip()
        if not line or ',' not in line:
            print(f"Skipping invalid line: {line}")
            continue
        try:
            product, url = line.split(',', 1)
            product_data.append((product.strip(), url.strip()))
        except ValueError as e:
            print(f"Error processing line: {line}. Error: {e}")
            continue

driver = webdriver.Chrome()
driver.get('https://www.amazon.com/SAMSUNG-Display-Watchfaces-Exercise-International/product-reviews/B0CW3VWC3X/ref=cm_cr_getr_d_paging_btm_prev_1?ie=UTF8&reviewerType=all_reviews&pageNumber=1')
time.sleep(20)

for product_name, url in product_data:
    print(f"Scraping reviews for: {product_name}")
    while url is not None:
        driver.get(url)
        time.sleep(3)
        html_data = BeautifulSoup(driver.page_source, 'html.parser')
        reviews = html_data.find_all('li', {'data-hook': 'review'})
        for review in reviews:
            user = review.find('span', {'class': 'a-profile-name'}).text.strip()
            raw_date = review.find('span', {'data-hook': 'review-date'}).text.strip()
            message = review.find('span', {'data-hook': 'review-body'}).text.strip()
            date = extract_date(raw_date)
            cursor.execute('''
                INSERT INTO reviews (Product, User, Date, Message)
                VALUES (?, ?, ?, ?)
            ''', (product_name, user, date, message))
        url_check = html_data.find('li', {'class': 'a-last'})
        if url_check and 'a-disabled' not in url_check.get('class', []):
            url = 'https://www.amazon.com' + url_check.a['href']
        else:
            url = None
    print(f"Finished scraping reviews for: {product_name}")
conn.commit()
driver.quit()

# Update sentiment for 'reviews' and 'data' tables
def update_sentiment(cursor, table_name):
    cursor.execute(f"SELECT SID, Message FROM {table_name}")
    rows = cursor.fetchall()
    for sentiment, sid in analyze_sentiment(rows):
        cursor.execute(f"UPDATE {table_name} SET Sentiment = ? WHERE SID = ?", (sentiment, sid))

update_sentiment(cursor, "reviews")
update_sentiment(cursor, "data")
conn.commit()

# Convert 'reviews' and 'data' date format
cursor.execute("PRAGMA table_info(reviews)")
columns = [column[1] for column in cursor.fetchall()]

if 'Dateconverted' not in columns:
    cursor.execute("ALTER TABLE reviews ADD COLUMN Dateconverted DATE")
else:
    print("Column 'Dateconverted' already exists.")

cursor.execute("SELECT SID, Date FROM reviews")
rows = cursor.fetchall()

def convert_date_format(date_str):
    try:
        parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return parsed_date.strftime("%Y-%m-%d")  # Format: YYYY-MM-DD
    except ValueError:
        return None

# Update 'Dateconverted' column for 'reviews'
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

        cursor.execute("UPDATE reviews SET Dateconverted = ? WHERE SID = ?", (new_date, SID))

# Convert 'data' table date format
cursor.execute(f"SELECT * FROM data")
rows = cursor.fetchall()

# Update 'Dateconverted' column for 'data'
for row in rows:
    row_id = row[0]
    original_date = row[3]
    converted_date = convert_date_format(original_date)

    if converted_date:
        cursor.execute(
            f"UPDATE data SET Dateconverted = ? WHERE SID = ?",
            (converted_date, row_id)
        )

conn.commit()
conn.close()


'''Amazon Data'''

# Step 1: Load Data
# Connect to the SQLite database and fetch relevant columns
conn = sqlite3.connect("sentiment.db")
query = """
SELECT SID, Product, Dateconverted AS date, Sentiment
FROM reviews
WHERE date IS NOT NULL AND Sentiment != ''
"""
df = pd.read_sql_query(query, conn)  # Load the query result into a pandas DataFrame
conn.close()  # Close the database connection

# Convert 'date' column to datetime format for easier analysis in line charts
df['date'] = pd.to_datetime(df['date'])

# Step 2: Transform Data
# Map Sentiment labels (e.g., "Positive", "Negative") to numerical Sentiment scores
Sentiment_map = {'Strong Positive': 2, 'Positive': 1, 'Neutral': 0, 'Negative': -1, 'Strong Negative': -2}
df['SentimentScore'] = df['Sentiment'].map(Sentiment_map)

# Calculate Sentiment trend: Group by Product and date, and compute the average Sentiment score
grouped_trend = df.groupby(['Product', 'date'])['SentimentScore'].mean().reset_index()

# Calculate Sentiment distribution: Count the occurrences of each Sentiment per Product
distribution = df.groupby(['Product', 'Sentiment']).size().reset_index(name='Counts')

# Calculate the total count of Sentiments per Product
total_counts = distribution.groupby('Product')['Counts'].sum().reset_index(name='Total')

# Merge the total counts with the distribution data to calculate percentage contribution
distribution = distribution.merge(total_counts, on='Product')
distribution['Percentage'] = (distribution['Counts'] / distribution['Total']) * 100

# Step 3: Visualizations
# Set the Seaborn style for consistent and clean plots
sns.set(style="whitegrid", palette="muted", font_scale=1.2)

# Get a list of unique Products and determine the number of rows required for plots
unique_Products = grouped_trend['Product'].unique()
num_Products = len(unique_Products)

# Define layout: Two plots (line chart + pie chart) for each Product
cols = 2
rows = (num_Products * 2 + cols - 1) // cols

# Create a figure and axes for subplots
fig, axes = plt.subplots(rows, cols, figsize=(16, rows * 5))
axes = axes.flatten()  # Flatten the axes array for easier iteration

# Add line plots (trend) and pie charts (distribution) for each Product
for i, Product in enumerate(unique_Products):
    # Line Chart: Plot Sentiment trend over time for the current product
    Product_data = grouped_trend[grouped_trend['Product'] == Product]
    ax = axes[i * 2]  # Select the appropriate subplot for the line chart
    sns.lineplot(data=Product_data, x='date', y='SentimentScore', ax=ax)
    ax.set_title(f"Sentiment Trend for {Product}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Average Sentiment Score")

    # Format x-axis dates for better readability
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Format dates as YYYY-MM-DD
    ax.xaxis.set_major_locator(mdates.MonthLocator())  # Show major ticks at the start of each month
    ax.tick_params(axis='x', rotation=45)  # Rotate x-axis labels for better visibility

    # Pie Chart: Plot Sentiment distribution for the current Product
    Product_distribution = distribution[distribution['Product'] == Product]
    pastel_colors = sns.color_palette("pastel")  # Use pastel colors for better visuals
    pie_colors = pastel_colors[:len(Product_distribution['Sentiment'])]  # Assign colors to pie sections
    ax = axes[i * 2 + 1]  # Select the subplot for the pie chart
    wedges, texts, autotexts = ax.pie(
        Product_distribution['Percentage'],
        labels=None,  # Exclude labels directly on the pie chart
        autopct='%1.1f%%',  # Show percentages with 1 decimal place
        startangle=140,  # Rotate the pie chart for consistent positioning
        colors=pie_colors,
        shadow=True  # Add shadow for better depth effect
    )

    # Adjust font size for percentage text
    for autotext in autotexts:
        autotext.set_fontsize(8)

    # Set the title of the pie chart
    ax.set_title(f"Sentiment Distribution for {Product}")

    # Add a legend to explain sentiment categories
    ax.legend(
        labels=Product_distribution['Sentiment'],  # Use Sentiment labels for the legend
        title="Sentiments",  # Title for the legend
        loc="center left",  # Place the legend on the left side of the chart
        bbox_to_anchor=(1, 0.5)  # Adjust legend position relative to the pie chart
    )

# Adjust layout to prevent overlapping elements
fig.suptitle("Amazon Visualization", fontsize=16, fontweight='bold', fontstyle='italic', y=0.98)# Add title here
plt.tight_layout()

# Display all plots
plt.show()

'''Mastodon Data'''

# Step 1: Load Data
# Connect to the SQLite database and fetch relevant columns
conn = sqlite3.connect("sentiment.db")
query = """
SELECT SID, Product, Dateconverted AS Date, Sentiment
FROM data
WHERE Date IS NOT NULL AND Sentiment != ''
"""
df = pd.read_sql_query(query, conn)
conn.close()

# Convert 'Date' column to datetime format for easier analysis
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

# Step 2: Transform Data
# Map Sentiment labels (e.g., "Positive", "Negative") to numerical Sentiment scores
Sentiment_map = {'Strong Positive': 2, 'Positive': 1, 'Neutral': 0, 'Negative': -1, 'Strong Negative': -2}
df['SentimentScore'] = df['Sentiment'].map(Sentiment_map)

# Calculate Sentiment trend: Group by Product and date, and compute the average Sentiment score
grouped_trend = df.groupby(['Product', 'Date'])['SentimentScore'].mean().reset_index()

# Calculate Sentiment distribution: Count the occurrences of each Sentiment per Product
distribution = df.groupby(['Product', 'Sentiment']).size().reset_index(name='Counts')

# Calculate the total count of Sentiments per Product
total_counts = distribution.groupby('Product')['Counts'].sum().reset_index(name='Total')

# Merge the total counts with the distribution data to calculate percentage contribution
distribution = distribution.merge(total_counts, on='Product')
distribution['Percentage'] = (distribution['Counts'] / distribution['Total']) * 100

# Step 3: Visualizations
# Set the Seaborn style for consistent and clean plots
sns.set(style="whitegrid", palette="muted", font_scale=1.2)

# Get a list of unique Products and determine the number of rows required for plots
unique_Products = grouped_trend['Product'].unique()
num_Products = len(unique_Products)

# Define layout: Two plots (line chart + pie chart) for each Product
cols = 2
rows = (num_Products * 2 + cols - 1) // cols

# Create a figure and axes for subplots
fig, axes = plt.subplots(rows, cols, figsize=(16, rows * 5))
axes = axes.flatten()

# Add line plots (trend) and pie charts (distribution) for each Product
for i, Product in enumerate(unique_Products):
    # Line Chart: Plot Sentiment trend over time for the current Product
    Product_data = grouped_trend[grouped_trend['Product'] == Product]
    if Product == 'Fitbit':
        Product_data = Product_data[Product_data['Date'] >= '2018-01-01']
    ax = axes[i * 2]
    sns.lineplot(data=Product_data, x='Date', y='SentimentScore', ax=ax)
    ax.set_title(f"Sentiment Trend for {Product}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Average Sentiment Score")

    # Format x-axis dates for better readability
    if Product == 'samsung watch':
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))  # 6-month intervals
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator())  # Monthly intervals

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Format dates as YYYY-MM-DD
    ax.tick_params(axis='x', rotation=45)

    # Pie Chart: Plot Sentiment distribution for the current Product
    Product_distribution = distribution[distribution['Product'] == Product]
    pastel_colors = sns.color_palette("pastel")
    pie_colors = pastel_colors[:len(Product_distribution['Sentiment'])]

    ax = axes[i * 2 + 1]
    wedges, texts, autotexts = ax.pie(
        Product_distribution['Percentage'],
        labels=None,
        autopct='%1.1f%%',
        startangle=140,
        colors=pie_colors,
        shadow=True
    )

    # Adjust font size for percentage text
    for autotext in autotexts:
        autotext.set_fontsize(8)

    # Set the title of the pie chart
    ax.set_title(f"Sentiment Distribution for {Product}")

    # Add a legend to explain Sentiment categories
    ax.legend(
        labels=Product_distribution['Sentiment'],
        title="Sentiments",
        loc="center left",
        bbox_to_anchor=(1, 0.5)
    )

# Adjust layout to prevent overlapping elements
fig.suptitle("Mastodon Visualization", fontsize=16, fontweight='bold', fontstyle='italic', y=0.98)

plt.tight_layout()

# Display all plots
plt.show()

