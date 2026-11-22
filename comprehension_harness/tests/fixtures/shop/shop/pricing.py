from narrate import narrate

TAX = 0.2


def with_tax(amount):
    rate = TAX
    narrate("The price **gains the tax**, `rate` of it.", lambda: {"amount": amount})
    return amount * (1 + rate)


def round_price(amount):
    return round(amount, 2)
