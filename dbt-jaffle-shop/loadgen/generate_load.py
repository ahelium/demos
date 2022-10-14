import random
import time

from psycopg2 import sql, errors, connect
from datetime import datetime
import barnum
import os

class Order:
    status_list = ['placed', 'shipped', 'completed', 'returned', 'return_pending']

    def __init__(self):
        self.user_id = random.randint(1, 100)
        self.status = random.choice(Order.status_list)
        self.order_date = datetime.now()


class Payment:
    method_list = ['credit_card', 'coupon', 'bank_transfer', 'gift_card']

    def __init__(self):
        self.payment_method = random.choice(Payment.method_list)
        self.amount = round(random.uniform(1000, 3000))


def main():

    try:
        conn = connect(
            user=os.getenv('PG_USER', 'postgres'),
            password=os.getenv('PG_PW'),
            host=os.getenv('PG_HOST'),
            port=os.getenv('PG_PORT', 5432),
            database=os.getenv('PG_DB', 'postgres')
        )

        cur = conn.cursor()
        print("\ncreated cursor object:", cur)

        for i in range(1, 1000):
            order = Order()

            customer_name = barnum.create_name()
            cur.execute("INSERT INTO customers (id, first_name, last_name) VALUES (%s, %s, %s) ON CONFLICT(id) DO NOTHING",
                        (order.user_id, customer_name[0], customer_name[1]))

            cur.execute("INSERT INTO orders (user_id, order_date, status) VALUES (%s, %s, %s)",
                    (order.user_id, order.order_date, order.status))

            if order.status == "placed":
                print(order.status)
                payment = Payment()

                cur.execute("INSERT INTO payments (order_id, payment_method, amount) VALUES (%s, %s, %s)",
                            (i, payment.payment_method, payment.amount))

            conn.commit()
            time.sleep(1)

        cur.close()
        conn.close()

    except errors.OperationalError as err:
        print("\npsycopg2 connect error:", err)
        conn = None
        cur = None

if __name__ == '__main__':
    main()