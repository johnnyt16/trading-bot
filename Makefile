# Makefile for Trading Bot

.PHONY: format lint test clean install

# Format code with black
format:
	black src/ scripts/ tests/ main.py --line-length 100
	isort src/ scripts/ tests/ main.py --profile black

# Run linting
lint:
	flake8 src/ scripts/ tests/ main.py --max-line-length=100
	pylint src/ scripts/ tests/ main.py

# Run tests
test:
	pytest tests/ -v

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov

# Install dependencies
install:
	pip install -r requirements.txt

# Format and lint
check: format lint

# Run everything
all: format lint test