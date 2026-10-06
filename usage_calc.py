#!/usr/bin/env python3
"""Compute this month's Claude Code spend vs. budget.

Budget/spend come from ~/.claude.json's cachedUsageUtilization block, the
same account-wide figures the CLI's own /usage command shows (refreshed by
the CLI during normal use). Per-model breakdown is a local-only estimate
from this machine's transcripts (not authoritative -- /usage's dollar
figure covers all devices; this breakdown is for relative share only).
"""
import glob
import json
import os
from calendar import monthrange
from datetime import datetime, timezone

CLAUDE_JSON_PATH = os.path.expanduser("~/.claude.json")
CONFIG_PATH = os.path.expanduser("~/.claude-meter/config.json")
PROJECTS_GLOB = os.path.expanduser("~/.claude/projects/**/*.jsonl")

# $/MTok, for the local by-model breakdown estimate only.
PRICING = {
    "claude-opus-5-5": {"in": 4.00, "out": 20.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"in": 2.00, "out": 10.00, "cache_read": 0.20},
    "claude-sonnet-5": {"in": 2.00, "out": 10.00, "cache_read": 0.20},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
    "claude-haiku-4-5": {"in": 1.00, "out": 5.00},
    "claude-fable-5-1": {"in": 10.00, "out": 50.00, "cache_read": 0.25},
    "claude-fable-5": {"in": 10.00, "out": 50.00, "cache_read": 0.25},
    "claude-opus-5": {"in": 5.00, "out": 25.00},
    "claude-opus-4-8": {"in": 5.00, "out": 25.00},
    "claude-opus-4-7": {"in": 5.00, "out": 25.00},
    "claude-opus-4-6": {"in": 5.00, "out": 25.00},
}


def rates(model):
    p = PRICING.get(model, {"in": 3.00, "out": 15.00})
    cache_read = p.get("cache_read", p["in"] * 0.1)
    write_5m = p.get("write_5m", p["in"] * 1.25)
    write_1h = p.get("write_1h", p["in"] * 2.0)
    return p["in"], p["out"], cache_read, write_5m, write_1h


def message_cost(model, usage):
    rate_in, rate_out, rate_read, rate_w5m, rate_w1h = rates(model)
    cache = usage.get("cache_creation", {}) or {}
    cost = (
        usage.get("input_tokens", 0) * rate_in
        + usage.get("output_tokens", 0) * rate_out
        + usage.get("cache_read_input_tokens", 0) * rate_read
        + cache.get("ephemeral_5m_input_tokens", 0) * rate_w5m
        + cache.get("ephemeral_1h_input_tokens", 0) * rate_w1h
    ) / 1_000_000
    return cost


def by_model_breakdown(now_local):
    seen_ids = set()
    by_model = {}
    for path in glob.glob(PROJECTS_GLOB, recursive=True):
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = entry.get("message", {})
                    if msg.get("role") != "assistant" or "usage" not in msg:
                        continue
                    ts = entry.get("timestamp")
                    if not ts:
                        continue
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(now_local.tzinfo)
                    if dt.year != now_local.year or dt.month != now_local.month:
                        continue
                    msg_id = msg.get("id")
                    if msg_id in seen_ids:
                        continue
                    seen_ids.add(msg_id)
                    model = msg.get("model", "unknown")
                    cost = message_cost(model, msg["usage"])
                    by_model[model] = by_model.get(model, 0.0) + cost
        except OSError:
            continue
    return by_model


def load_authoritative_spend():
    """Read the real account spend/budget cached by the CLI, if present."""
    try:
        with open(CLAUDE_JSON_PATH) as f:
            data = json.load(f)
        util = data["cachedUsageUtilization"]["utilization"]
        spend = util.get("spend")
        if not spend or not spend.get("enabled"):
            return None
        used = spend["used"]
        limit = spend["limit"]
        total = used["amount_minor"] / (10 ** used["exponent"])
        budget = limit["amount_minor"] / (10 ** limit["exponent"])
        return total, budget
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError):
        return None


def load_manual_budget():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump({"budget_usd": 100.0}, f, indent=2)
        return 100.0
    with open(CONFIG_PATH) as f:
        return json.load(f).get("budget_usd", 100.0)


def main():
    now_local = datetime.now().astimezone()
    authoritative = load_authoritative_spend()

    by_model = by_model_breakdown(now_local)

    if authoritative is not None:
        total, budget = authoritative
        source = "account"
    else:
        total = sum(by_model.values())
        budget = load_manual_budget()
        source = "local_estimate"

    days_in_month = monthrange(now_local.year, now_local.month)[1]
    expected = budget * (now_local.day / days_in_month)
    status = "over" if total > expected else "under"

    print(json.dumps({
        "total": round(total, 2),
        "budget": round(budget, 2),
        "expected": round(expected, 2),
        "status": status,
        "source": source,
        "by_model": {k: round(v, 2) for k, v in sorted(by_model.items(), key=lambda kv: -kv[1])},
    }))


if __name__ == "__main__":
    main()
