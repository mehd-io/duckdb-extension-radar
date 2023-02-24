install : 
	poetry install

pipeline : 
	poetry run python duckdb_extension_radar.py

format : 
	black .
	isort .

test : 
	pytest
