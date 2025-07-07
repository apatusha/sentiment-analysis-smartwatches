
# Sentiment Analysis of Smartwatch Reviews

## Project Overview

This project was developed as part of the course **"Data Analysis and Visualisation with Python"** in the Europa-Universität Viadrina, in collaboration with my classmates.

We built a full sentiment analysis pipeline in Python to collect, process, classify, and visualize user opinions about smartwatch products, using **Amazon customer reviews** and **Mastodon posts**.

The project includes:
- Custom scraping logic for Amazon (via Selenium)
- API-based extraction from Mastodon
- Classification into 5 sentiment categories using VADER
- Time-series and distribution analysis of sentiment
- Visualization using **Matplotlib**, **Seaborn**, and **Power BI**
  


## Data Sources

1. **Mastodon API**:  
  Search terms are defined in [`terms.json`](terms.json), and messages are retrieved via authenticated requests.

2. **Amazon Reviews**:  
  Product names and review page URLs are stored in [`terms.txt`](terms.txt). Selenium is used to load pages and extract reviews.

Data is stored in an SQLite database called [`sentiment.db`](sentiment.db), with two main tables: `data` (Mastodon) and `reviews` (Amazon).

## Sentiment Labels

Each text message is assigned one of the following categories:
- Strong Positive  
- Positive  
- Neutral  
- Negative  
- Strong Negative

## Visualizations

We used both **Python** and **Power BI** for visualizations:
- Line plots show sentiment trends over time.
- Pie charts show distribution of sentiment per product.

##  Key Python Libraries

The following Python libraries are required to run the project: 

`beautifulsoup4`, `blurhash`, `certifi`, `charset-normalizer`, `decorator`,  
`idna`, `Mastodon.py`, `matplotlib`, `pandas`, `python-dateutil`,  
`python-magic-bin`, `requests`, `seaborn`, `selenium`, `six`,  
`soupsieve`, `urllib3`, `vaderSentiment`

## ✅ Results

This project successfully implemented a sentiment analysis pipeline to evaluate public perception of various smartwatch products based on data from Amazon and Mastodon.

Key outcomes:
- Extracted over 500 posts and reviews across five smartwatch models.
- Classified sentiments into five categories with VADER and stored them in a structured database.
- Identified consistent sentiment trends over time, with visualizations showing:
  - Fluctuations in user satisfaction for each product
  - Distribution of sentiment classes across brands
- Created interactive dashboards in Power BI for further exploration and presentation.

The analysis provides actionable insights into user satisfaction and market sentiment.


