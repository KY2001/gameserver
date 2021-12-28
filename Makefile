run:
	uvicorn app.api:app --reload

format:
	isort app tests  # import文の並び順をsort
	black app tests  # codeformat

test:
	pytest -sv tests
