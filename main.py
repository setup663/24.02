import sys
from decimal import Decimal
import pymysql
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget
from inter import Ui_MainWindow


class MoneyTransferApp(Ui_MainWindow):
    def __init__(self, window):
        self.setupUi(window)

        self.conn = None
        self.load_data()
        self.setup_connections()

    def setup_connections(self):
        self.btn_transfer.clicked.connect(self.make_transfer)
        self.cmb_country.currentIndexChanged.connect(self.update_commission)

    def load_data(self):
        try:
            self.conn = pymysql.connect(
                host='localhost',
                user='root',
                password='',
                database='money_transfer',
                autocommit=True
            )

            # Загрузка получателей
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT id, name, country_id FROM users")
                self.cmb_receiver.clear()
                for user_id, name, country_id in cursor.fetchall():
                    self.cmb_receiver.addItem(name, userData=(user_id, country_id))

            # Загрузка стран и комиссий
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT c.id, c.name, cr.rate 
                    FROM countries c
                    JOIN commission_rates cr ON c.id = cr.country_id
                """)
                self.cmb_country.clear()
                for country_id, name, rate in cursor.fetchall():
                    self.cmb_country.addItem(
                        f"{name} ({float(rate) * 100:.0f}%)",
                        userData=(country_id, Decimal(str(rate)))
                    )

            self.load_history()

        except Exception as e:
            QMessageBox.critical(None, 'Ошибка', f'Ошибка БД: {str(e)}')

    def update_commission(self):
        if self.cmb_country.currentIndex() >= 0:
            _, rate = self.cmb_country.currentData()
            self.lbl_commission.setText(f"Комиссия: {rate * 100:.2f}%")

    def make_transfer(self):
        try:
            receiver_id, _ = self.cmb_receiver.currentData()
            country_id, rate = self.cmb_country.currentData()

            amount_str = self.txt_amount.text().replace(',', '.')
            amount = Decimal(amount_str)
            commission = (amount * rate).quantize(Decimal('0.00'))

            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO transfers 
                    (receiver_id, country_id, amount, commission)
                    VALUES (%s, %s, %s, %s)
                """, (receiver_id, country_id, str(amount), str(commission)))

            self.txt_amount.clear()
            self.load_history()
            QMessageBox.information(
                None,
                'Успех',
                f"Перевод на {amount}₽\nКомиссия: {commission}₽\nИтого: {amount + commission}₽"
            )

        except ValueError:
            QMessageBox.critical(None, 'Ошибка', 'Некорректная сумма перевода')
        except Exception as e:
            QMessageBox.critical(None, 'Ошибка', f'Ошибка перевода: {str(e)}')

    def load_history(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT u.name, c.name, t.amount, t.commission, t.transfer_date 
                    FROM transfers t
                    JOIN users u ON t.receiver_id = u.id
                    JOIN countries c ON t.country_id = c.id
                    ORDER BY t.transfer_date DESC
                """)

                history = ""
                for receiver, country, amount, commission, date in cursor.fetchall():
                    history += (
                        f"[{date}] {receiver} ({country}): "
                        f"{Decimal(str(amount))}₽ + "
                        f"комиссия {Decimal(str(commission))}₽\n"
                    )

                self.txt_history.setPlainText(history)

        except Exception as e:
            QMessageBox.critical(None, 'Ошибка', f'Ошибка загрузки истории: {str(e)}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QWidget()
    ui = MoneyTransferApp(window)
    window.show()
    sys.exit(app.exec())