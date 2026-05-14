PALETTE = {
    "copper": 0xD97757,
    "amber":  0xFFD166,
    "pink":   0xFF6B9D,
    "brown":  0x8B4513,
    "white":  0xFFFFFF,
    "cream":  0xB8997E,
    "dim":    0x2A2014,
    "off":    0x000000,
}


def format_tokens(n):
    if n is None:
        return "0"
    if n >= 1_000_000:
        return "{:.1f}M".format(n / 1_000_000)
    if n >= 1_000:
        return "{:.0f}k".format(n / 1_000)
    return str(int(n))


def short_model(model):
    if not model:
        return "?"
    if "opus" in model:
        return "OPUS"
    if "sonnet" in model:
        return "SONNET"
    if "haiku" in model:
        return "HAIKU"
    return model[:8].upper()


def format_duration(minutes):
    if minutes is None or minutes < 0:
        return ""
    minutes = int(minutes)
    if minutes >= 60:
        return "{}h {}m".format(minutes // 60, minutes % 60)
    return "{}m".format(minutes)


def bar_color_for_pct(pct):
    if pct is None or pct < 60:
        return PALETTE["amber"]
    if pct < 85:
        return PALETTE["copper"]
    return PALETTE["pink"]
