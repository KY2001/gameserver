run:
	uvicorn app.api:app --reload

format:
	isort app tests  # import文の並び順をsort
	black app tests  # codeformat

test:
	pytest -sv tests # User・Room APIのテストを実行, -s: テスト中の標準出力を表示, -v: より詳細なテスト結果を表示
	mysql webapp < schema.sql