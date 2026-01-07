# config.py

# Define the forwarding tasks. Each task is a dictionary that specifies the
# source channels, target channels, and AI modifications.
TASKS = [
    {
        "name": "Task 1: News and Updates",
        "sources": ["@news_channel1", "@updates_channel2", "@tech_channel3"],
        "targets": ["@my_target_channel1"],
        "ai_options": {
            "reword": True,
            "summarize": False,
            "header": "📢 Breaking News",
            "footer": "Powered by MyBrand",
            "watermark": {
                "replace_from": "Example.com",
                "replace_to": "MyBrand"
            }
        }
    },
    {
        "name": "Task 2: Sports and Entertainment",
        "sources": ["@sports_channel", "@entertainment_channel", "@music_channel"],
        "targets": ["@my_sports_channel", "@my_entertainment_channel"],
        "ai_options": {
            "reword": False,
            "summarize": True,
            "summary_length": 100,  # Max length in words
            "header": None,
            "footer": "Via MyBrand",
            "watermark": {
                "replace_from": "SourceBrand",
                "replace_to": "MyBrand"
            }
        }
    }
]
