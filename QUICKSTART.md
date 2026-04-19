# Lazarus Protocol — Quick Start

## 5-minute setup

1. Clone and install: `pip install -r requirements.txt`
2. Copy environment template: `cp .env.example .env`
3. Edit `.env` with your SendGrid API key and email addresses
4. Run setup wizard: `python3 -m cli.main init`
5. Start agent: `python3 -m cli.main agent start`
6. Check status: `python3 -m cli.main status`
7. Open dashboard: `http://localhost:6666`

## Daily check-in

```bash
python3 -m cli.main ping
```

## Emergency freeze

```bash
python3 -m cli.main freeze --days 30
```

## Running Tests

### Unit Tests (no external services required)

```bash
python3 -m pytest tests/ -v
```

### Integration Tests (requires SendGrid API key)

Integration tests send **real emails** through SendGrid. They are skipped
automatically if `SENDGRID_API_KEY` is not configured.

```bash
# Run ALL tests (integration tests will be skipped if not configured)
python3 -m pytest tests/ -v

# Run ONLY integration tests
python3 -m pytest tests/test_sendgrid_integration.py -v -m integration

# Skip integration tests explicitly
python3 -m pytest tests/ -v -m "not integration"
```

**Prerequisites for integration tests:**
1. Set `SENDGRID_API_KEY` in your `.env` file (not the placeholder value)
2. Set `ALERT_FROM_EMAIL` to a verified sender in your SendGrid account
3. Set `ALERT_TO_EMAIL` to your personal email address

> ⚠️ Integration tests send real emails. You will receive test messages at
> the `ALERT_TO_EMAIL` address. These are safe to ignore/delete.
