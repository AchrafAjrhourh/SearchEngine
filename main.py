import logging
from config import setup_logging
from extractor import fetch_real_news
from summarizer import summarize_news

if __name__ == "__main__":
    # 1. Initialize settings
    setup_logging()
    
    logging.info("--- APPLICATION STARTED ---")
    
    # 2. Get user input
    target_figure = input("\n🕵️ Enter the name of the figure you want to search for: ")
    
    # 3. Extract the data
    live_data = fetch_real_news(target_figure)
    
    # 4. Summarize and Print
    if live_data:
        final_summary = summarize_news(target_figure, live_data)
        
        print("\n" + "="*50)
        print("FINAL OUTPUT TO USER")
        print("="*50)
        print(final_summary)
    else:
        logging.warning("No data was found, skipping summarization.")
        
    logging.info("--- APPLICATION FINISHED ---")