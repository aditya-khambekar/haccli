#!/bin/env python3

import requests
import re
from bs4 import BeautifulSoup
from getpass import getpass
import json
import keyring
from platformdirs import user_config_dir
import os

hac_url = "homeaccess.katyisd.org"

config_dir = user_config_dir("haccli")
config_file = config_dir + "/storedlogin.json"

s = requests.Session()
try:
    with open(config_file, "r") as f:
        contents = f.read()
except FileNotFoundError:
    contents = ""

if len(contents.strip()) == 0:
    contents = "{}"

data = json.loads(contents)

if "username" in data and "password" in data:
    username = data["username"]
    password = data["password"]
    print("Logging in with saved password...")
else:
    username = input("ID: ")
    password = getpass()

if "store_password" not in data:
    response = input("Store password in plain text file? [y/N] ")
    if (response.lower().startswith("y")):
        data["store_password"] = True
        data["username"] = username
        data["password"] = password

        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        with open(config_file, "w+") as f:
            f.write(json.dumps(data))

r = s.get(f'https://{hac_url}/HomeAccess/Account/LogOn')

request_verification_token = re.search(
    '(?<=<input name="__RequestVerificationToken" type="hidden" value=")(.*?)(?=")', r.text).group(1)

loginData = {
    "__RequestVerificationToken": request_verification_token,
    "Database": 10,
    "LogOnDetails.UserName": username,
    "LogOnDetails.Password": password
}

r = s.post(f'https://{hac_url}/HomeAccess/Account/LogOn', data=loginData)
soup = BeautifulSoup(r.text, "lxml")
validation_error_div = soup.find("div", class_="validation-summary-errors")

request_error_div = soup.find("div", class_="caption")

if (validation_error_div is not None):
    print(validation_error_div.find("li").text.strip())
elif (request_error_div is not None):
    print(request_error_div.text.strip())
else:
    print("Login success!")

print("Getting grades...")

r = s.get(f'https://{hac_url}/HomeAccess/Content/Student/Assignments.aspx')

print()

soup = BeautifulSoup(r.text, "lxml")

classes = soup.find_all("div", class_="AssignmentClass")

for i, result in enumerate(classes):
    title_tag = result.find("a")
    class_name = " ".join(title_tag.text.strip().split(" ")[3:]).strip()

    class_average_element = result.find(
        id=f"plnMain_rptAssigmnetsByCourse_lblHdrAverage_{i}")
    class_average = class_average_element.text[18:]

    print(f"\033[1m{class_name:<52}\033[4m{class_average}\033[0m")

    assignments_table = result.find("table", class_="sg-asp-table")
    if assignments_table is None:
        print("  No assignments\n")
        continue

    assignments_rows = assignments_table.find_all(
        "tr", class_="sg-asp-table-data-row")
    for assignment in assignments_rows:
        cells = assignment.find_all("td")
        due_date = cells[0].text.strip()
        date_assigned = cells[1].text.strip()
        assignment_name = cells[2].text.strip().splitlines()[0]
        category = cells[3].text.strip()
        score = cells[4].text.strip()
        total_points = cells[5].text.strip()
        weight = cells[6].text.strip()
        weighted_score = cells[7].text.strip()
        weighted_total_points = cells[8].text.strip()
        percentage = cells[9].text.strip()

        category_colors = {
            "Other": "",
            "Minor": "\033[1;33m",
            "Major": "\033[0;31m\033[1m"
        }

        print(
            f"{category_colors[category]}  {assignment_name + ' (' + category + ')':<50}{'-' if score == '' else score}\033[0m")

    print()
