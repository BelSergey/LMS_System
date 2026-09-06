import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_product(name: str):
    return stripe.Product.create(name=name)


def create_stripe_price(product_id: str, amount):
    return stripe.Price.create(
        currency='usd',
        unit_amount=int(amount * 100),
        product=product_id,
    )


def create_stripe_checkout_session(price_id: str):
    return stripe.checkout.Session.create(
        line_items=[{'price': price_id, 'quantity': 1}],
        mode='payment',
        success_url='http://127.0.0.1:8000/users/api/payments/success/',
        cancel_url='http://127.0.0.1:8000/users/api/payments/cancel/',
    )


def retrieve_stripe_session(session_id: str):
    return stripe.checkout.Session.retrieve(session_id)