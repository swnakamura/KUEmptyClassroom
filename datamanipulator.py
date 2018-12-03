from pathlib import Path
import json
import sys
from bs4 import BeautifulSoup
from selenium import webdriver
from time import sleep
from tqdm import tqdm
import re
from pymongo import *


class KUWebDriver():

    def __init__(self):
        # login process
        with open("id_and_pass.json") as f:
            login_info = json.load(f)
        self.login_url = "https://www.k.kyoto-u.ac.jp/student/la/top"
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1200x600')
        self.driver = webdriver.Chrome(
            "./chromedriver", chrome_options=options)

        login_url = "https://www.k.kyoto-u.ac.jp/student/la/top"
        self.driver.get(login_url)
        self.driver.find_element_by_id(
            "username").send_keys(login_info["KU_ecs_ID"])
        self.driver.find_element_by_id("password").send_keys(
            login_info["KU_ecs_PASSWORD"])
        self.driver.find_element_by_name("_eventId_proceed").click()

    def fetchAllLASyllabusData(self, wait_sec=1):
        # # go to syllabus
        # self.syllabus_url = "https://www.k.kyoto-u.ac.jp/student/la/syllabus/top"
        # self.driver.get(self.syllabus_url)
        # # click search button
        # self.driver.find_elements_by_class_name(
            # "syllabus_search_submit_button")[0].click()

        for k in tqdm(range(305)):
            self.driver.get("https://www.k.kyoto-u.ac.jp/student/la/syllabus/detail?condition.courseType=&condition.seriesName=&condition.familyFieldName=&condition.lectureStatusNo=1&condition.langNum=&condition.semester=&condition.targetStudent=0&condition.courseTitle=&condition.courseTitleEn=&condition.teacherName=&condition.teacherNameEn=&condition.itemInPage=10&condition.syutyu=false&condition.lectureCode=&page="+str(k))
            with open("./data/syllabus/LA/"+str(k)+".html", 'w') as f:  # 0-indexed
                f.write(self.driver.page_source)
            sleep(wait_sec)

    def quitDriver(self):
        self.driver.quit()


class KUClassroomDatabase:

    def __init__(self):
        self.client = MongoClient('localhost', 27017)
        self.db = self.client.class_database
        self.collection = self.db.class_collection

    def extractTimeAndLocation(self, path):
        # initialization
        # self.collection.delete_many({})
        non_space_finder = re.compile("\S")
        for html_doc in sorted(Path(path).glob("*.html")):
            with open(html_doc, 'r') as html_file:
                soup = BeautifulSoup(html_file, 'html5lib')
                for item in soup.body.div.div.find("div", id="wrapper").find("div", class_="contents")("center", recursive=False)[1].find_all("table", border="1"):

                    # 曜時限
                    classtime = item.tbody.find_all("tr", recursive=False)[5].tr(
                        "td", recursive=False)[1].span.contents[0]
                    # m = classtime.rfind(' ')
                    m = re.search(non_space_finder, classtime)
                    classtimelist = self.listofclasstime(classtime[m.start():])

                    # 場所
                    classplace = item.tbody.find_all("tr", recursive=False)[5].tr(
                        "td", recursive=False)[3].span.contents[0]
                    # 英語で教室名が書いてあるとスペースが入ってしまうのでそれを防ぐ
                    # m = classplace.rfind('   ')
                    m = re.search(non_space_finder, classplace)
                    classplace = classplace[m.start():]

                    # 授業名
                    classtitle = item.tbody.find("tr", valign="top").tbody.find(
                        "tr", recursive=False, style="vertical-align: top").b.contents[0]
                    m = re.search(non_space_finder, classtitle)
                    classtitle = classtitle[m.start():]

                    new_post = {
                        "time": classtimelist,
                        "venue": classplace,
                        "type": "LA",
                        "title": classtitle
                    }

                    result = self.collection.insert_one(new_post)

    def listofclasstime(self, classtime):
        """中点・で分割する"""
        match = re.split("・", classtime)
        return match

    def showDatabaseContents(self):
        """テスト用"""
        uniqueclassplacelist = self.collection.distinct("venue")
        classlist = []
        completeclassset = set(['月1', '月2', '月3', '月4', '月5', '木1', '木2', '木3', '木4', '木5', '水1',
                                '水2', '水3', '水4', '水5', '火1', '火2', '火3', '火4', '火5', '金1', '金2', '金3', '金4', '金5'])
        for venueiter in range(len(uniqueclassplacelist)):
            if uniqueclassplacelist[venueiter][0] == '4':
                for found in self.collection.find({"venue": uniqueclassplacelist[venueiter]}):
                    classlist.extend(found["time"])
                print(uniqueclassplacelist[venueiter])

                open_classroom=sorted(completeclassset-set(classlist))
                print(open_classroom)#空いている時間
                classlist = []

    def teach_me_open_classroom(self, desired_time):
        uniqueclassplacelist = self.collection.distinct("venue")
        completeclassset = set(['月1', '月2', '月3', '月4', '月5', '木1', '木2', '木3', '木4', '木5', '水1',
                                '水2', '水3', '水4', '水5', '火1', '火2', '火3', '火4', '火5', '金1', '金2', '金3', '金4', '金5'])
        day=desired_time[0]
        period=int(desired_time[1])
        classroomlist = []

        print(day+"曜日"+str(period)+"限からの教室日程ですが")

        for venueiter in range(len(uniqueclassplacelist)):
            if uniqueclassplacelist[venueiter][0] == '4':
                for found in self.collection.find({"venue": uniqueclassplacelist[venueiter]}):
                    classroomlist.extend(found["time"])

                open_classroom=sorted(completeclassset-set(classroomlist))
                classroomlist = []

                timeiter=period-1
                while day+str(timeiter+1) in open_classroom and timeiter<5:
                    timeiter+=1
                if timeiter>=period:
                    print("\t"+uniqueclassplacelist[venueiter]+"が"+str(timeiter)+"限まで使用可能です")


if __name__ == '__main__':
    if sys.argv[1] == 'f':  # fetch
        driver = KUWebDriver()
        driver.fetchAllLASyllabusData()
        driver.quitDriver()
    elif sys.argv[1] == 'e':  # extract
        database = KUClassroomDatabase()
        database.extractTimeAndLocation("./data/syllabus/LA")
    elif sys.argv[1] == 's':  # search
        database = KUClassroomDatabase()
        # database.showDatabaseContents()
        for i in range(1,6):
            database.teach_me_open_classroom("火"+str(i))
