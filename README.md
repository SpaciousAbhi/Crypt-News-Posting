# Telegram Crypto News Bot (Minimal + Emojis)

Tracks top crypto Twitter sources, rewrites via LLaMA3 with emojis, and posts summaries to your Telegram channel.

## Setup
1. Clone repo
2. Copy `.env.example` → `.env`
3. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
4. Run locally:
   ```bash
   python main.py
   ```

## Deploy on Heroku
```bash
heroku create your-app
heroku config:set \
  TELEGRAM_BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d '=' -f2) \
  TELEGRAM_CHANNEL_ID=$(grep TELEGRAM_CHANNEL_ID .env | cut -d '=' -f2) \
  GROQ_API_KEY=$(grep GROQ_API_KEY .env | cut -d '=' -f2) \
  POLL_INTERVAL=300 \
  TWITTER_ACCOUNTS=@Cointelegraph,@CoinDesk,@BitcoinCom,@TheBlock__,@BloombergCrypto,@BeInCrypto
git push heroku main
heroku ps:scale worker=1
```
