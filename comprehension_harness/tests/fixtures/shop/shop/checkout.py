from narrate import event, narrate, planned
from shop.pricing import round_price, with_tax


class Basket:
    def __init__(self, lines):
        self.lines = lines

    def total(self):
        subtotal = sum(line.price for line in self.lines)
        narrate("The basket **adds its lines** before `with_tax`.", lambda: {"subtotal": subtotal})
        return round_price(with_tax(subtotal))


def pay(basket):
    event("The customer presses Pay.")
    amount = basket.total()
    planned("gift-cards#deduct-the-card", "The amount due **loses the card's balance**.")
    return charge(amount)


def charge(amount):
    narrate("The amount **is charged**.", lambda: {"amount": amount})
    return {"charged": amount}


def refund(amount):
    planned("gift-cards#refund-to-card", "A refund goes back to the card first.")
    raise NotImplementedError("planned: gift-cards#refund-to-card")


def pay_all(baskets):
    return [pay(basket) for basket in baskets]
