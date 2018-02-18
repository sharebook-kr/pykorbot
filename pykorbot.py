import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic
import pykorbit
import time
import csv
import os


# 코인
COIN = ["btc_krw", "bch_krw", "btg_krw", "eth_krw", "etc_krw", "xrp_krw"]
COIN_NAMES = ["비트코인", "비트코인 캐시", "비트코인 골드", "이더리움", "이더리움 클래식", "리플"]

form_class = uic.loadUiType("./ui/window.ui")[0]


# 실시간 시세를 조회하는 클래스
class PriceChecker(QThread):
    finished = pyqtSignal(list, list)

    def run(self):
        # 코인 현재가
        price_list = []
        rate_list = []

        for coin in COIN:
            price = pykorbit.get_current_price(coin)
            rate = self.get_rate_24(coin)
            time.sleep(0.2)

            price_list.append(price)
            rate_list.append(rate)

        # 시그널 발생
        self.finished.emit(price_list, rate_list)

    @staticmethod
    def get_rate_24(currency):
        # 24 시간 체결 데이터 요청
        contents = pykorbit.get_transaction_data(currency, interval="day")

        # 24시간 전 transaction
        transaction = contents[-1]
        before_price = int(transaction['price'])

        # 현재 transaction
        transaction = contents[0]
        current_price = int(transaction['price'])

        rate = ((current_price - before_price) * 100) / before_price
        return rate


# 포트폴리오를 조회하는 클래스
class BalanceChecker(QThread):
    balance_finished = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.korbit = None

    def set_korbit_instance(self, korbit):
        self.korbit = korbit

    def run(self):
        if self.korbit is not None:
            balance = self.korbit.get_balances()
            self.balance_finished.emit(balance)


# 메인 윈도우
class MyWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.login_status = False

        self.setWindowIcon(QIcon("./ui/icon.png"))
        self.setupUi(self)
        self.setFixedSize(self.size())

        self.tableWidget.setRowCount(len(COIN))
        self.tableWidget_2.setRowCount(len(COIN))

        self._auto_load()
        self._create_threads()                                  # 스레드 생성
        self._set_signal_slot()                                 # 시그널/슬롯 설정
        self._create_timers()                                   # 타이머 생성

    def _auto_load(self):
        flist = os.listdir()
        if "keys.csv" in flist:
            self.textEdit.insertPlainText("keys.csv 파일을 자동 로드 했습니다.\n")
            self._load_key_secret("./keys.csv")

    def _create_threads(self):
        self.worker = PriceChecker()
        self.worker.finished.connect(self.display_price)

        self.balance_worker = BalanceChecker()
        self.balance_worker.balance_finished.connect(self.display_balance)

    def _create_timers(self):
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.timeout)

        self.timer2 = QTimer(self)
        self.timer2.start(3000)
        self.timer2.timeout.connect(self.timeout2)

        self.timer3 = QTimer(self)
        self.timer3.start(5000)
        self.timer3.timeout.connect(self.timeout3)

    def _set_signal_slot(self):
        self.pushButton_2.clicked.connect(self.open_file_dialog)
        self.pushButton.clicked.connect(self._login)

    def _login(self):
        self.email = self.lineEdit.text()
        self.password = self.lineEdit_2.text()
        self.korbit = pykorbit.Korbit(self.email, self.password, self.key, self.secret)
        self.login_status = True

    def _get_cur_time(self):
        cur_time = QTime.currentTime()
        self.str_time = cur_time.toString("hh:mm:ss")

    def timeout(self):
        self._get_cur_time()
        self.statusBar().showMessage("현재 시간: " + self.str_time + " | 코빗 접속 중 | ")

    def timeout2(self):
        self.worker.start()

    def timeout3(self):
        if self.login_status is True:
            if self.balance_worker.korbit is None:
                self.balance_worker.set_korbit_instance(self.korbit)
            self.balance_worker.start()

    def open_file_dialog(self):
        fpath = QFileDialog.getOpenFileName(self)[0]
        self._load_key_secret(fpath)

    def _load_key_secret(self, fpath):
        # csv 파일 로드
        f = open(fpath)
        reader = csv.reader(f)
        lines = list(reader)
        f.close()

        # 위젯 출력
        self.key = lines[1][0]
        self.secret = lines[1][1]
        self.lineEdit_3.setText(self.key)
        self.lineEdit_4.setText(self.secret)

    @pyqtSlot(dict)
    def display_balance(self, balance):
        btc_avail = float(balance['btc']['available']) + float(balance['btc']['trade_in_use'])
        bch_avail = float(balance['bch']['available']) + float(balance['bch']['trade_in_use'])
        btg_avail = float(balance['btg']['available']) + float(balance['btg']['trade_in_use'])
        eth_avail = float(balance['eth']['available']) + float(balance['eth']['trade_in_use'])
        etc_avail = float(balance['etc']['available']) + float(balance['etc']['trade_in_use'])
        xrp_avail = float(balance['xrp']['available']) + float(balance['xrp']['trade_in_use'])
        hold_list = [btc_avail, bch_avail, btg_avail, eth_avail, etc_avail, xrp_avail]

        for i, coin in enumerate(COIN_NAMES):
            # 코인 이름
            coin_name = QTableWidgetItem(coin)
            coin_name.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)

            # 보유량
            hold_item = QTableWidgetItem(str(hold_list[i]))
            hold_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)

            # 현재가
            price = hold_list[i] * float(self.coin_cur_price[i])
            comma_price = format(int(price), ',d')
            price_item = QTableWidgetItem(comma_price)
            price_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)

            self.tableWidget_2.setItem(i, 0, coin_name)
            self.tableWidget_2.setItem(i, 1, hold_item)
            self.tableWidget_2.setItem(i, 2, price_item)


    @pyqtSlot(list, list)
    def display_price(self, price, rate):
        self.coin_cur_price = price

        self.textEdit.insertPlainText("시세 조회 데이터 갱신 완료 (%s)\n" % self.str_time)

        for i, coin in enumerate(COIN_NAMES):
            # 코인 이름
            coin_name = QTableWidgetItem(coin)
            coin_name.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)

            # 현재가
            comma_price = format(int(price[i]), ',d')
            price_item = QTableWidgetItem(comma_price)
            price_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)

            # 변동률
            rate_format = "%.2f%%" % rate[i]
            rate_item = QTableWidgetItem(rate_format)
            rate_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)

            self.tableWidget.setItem(i, 0, coin_name)
            self.tableWidget.setItem(i, 1, price_item)
            self.tableWidget.setItem(i, 2, rate_item)

        self.tableWidget.resizeColumnsToContents()


app = QApplication(sys.argv)
window = MyWindow()
window.show()
app.exec_()


