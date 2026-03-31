ProjectRoot/
├── main.py              # 🏠 表札（Streamlitのメインエンジン）
├── output_crypt_tech.py # 📝 鑑定書発行所（分析レポート統合）
├── finnews.db           # 📦 金庫の実体（SQLiteファイル）
├── src/
│   ├── data/            # 🚚 搬入（DataLoader, NewsFetcher, NewsLoader）
│   ├── logic/           # 🧠 脳みそ（Analytics, Judgement, Sentiment）
│   │   ├── crypt_sentiment.py
│   │   └── crypt_sentiment_models.py  # 🗄️ 金庫の設計図（DB定義） ★ココ！
│   └── ui/              # 🎨 内装（SKIN, Components）
