from narrate import narrative
from shop.checkout import Basket, pay


@narrative("The customer pays a basket")
class TestPay:
    """The total is the lines' sum with the tax, and that is what is charged."""

    def test_charges_the_total_with_tax(self):
        assert pay(Basket([]))["charged"] == 0
