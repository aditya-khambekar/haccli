import requests
import re
from bs4 import BeautifulSoup
from getpass import getpass
import json
import keyring
from platformdirs import user_config_dir
import os
from halo import Halo

hac_url = "homeaccess.katyisd.org"
SERVICE_NAME = "haccli"

config_dir = user_config_dir("haccli")
config_file = config_dir + "/config.json"

print(config_dir)

s = requests.Session()

try:
    with open(config_file, "r") as f:
        contents = f.read()
except FileNotFoundError:
    contents = ""

if len(contents.strip()) == 0:
    contents = "{}"

config = json.loads(contents)

saved_username = config.get("username")
password = None

if saved_username:
    try:
        password = keyring.get_password(SERVICE_NAME, saved_username)
        if password:
            print(f"Found saved credentials for: {saved_username}")
            username = saved_username
        else:
            print(f"Username found ({saved_username}) but no password in keyring")
            username = saved_username
            password = getpass("Password: ")
    except Exception as e:
        print(f"Error accessing keyring: {e}")
        username = input("ID: ")
        password = getpass("Password: ")
else:
    username = input("ID: ")
    password = input("Password: ")


if "save_credentials" not in config:
    save_choice = input("Save credentials securely in system keyring? [y/N] ").lower().strip()

    if save_choice.startswith("y"):
        config["save_credentials"] = True
        config["username"] = username

        # Save password to system keyring
        try:
            keyring.set_password(SERVICE_NAME, username, password)
            print("✓ Credentials saved securely to system keyring")
        except Exception as e:
            print(f"✗ Failed to save to keyring: {e}")
            config["save_credentials"] = False
    else:
        config["save_credentials"] = False

    # Save non-sensitive config
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    with open(config_file, "w") as f:
        f.write(json.dumps(config, indent=2))

with Halo(text='Connecting to HomeAccess...', spinner='dots') as spinner:
    r = s.get(f'https://{hac_url}/HomeAccess/Account/LogOn')
    spinner.succeed('Connected to HomeAccess')

request_verification_token = re.search(
    '(?<=<input name="__RequestVerificationToken" type="hidden" value=")(.*?)(?=")', r.text).group(1)

loginData = {
    "__RequestVerificationToken": request_verification_token,
    "Database": 10,
    "LogOnDetails.UserName": username,
    "LogOnDetails.Password": password
}

with Halo(text='Logging in...', spinner='dots') as spinner:
    r = s.post(f'https://{hac_url}/HomeAccess/Account/LogOn', data=loginData)
    soup = BeautifulSoup(r.text, "lxml")
    validation_error_div = soup.find("div", class_="validation-summary-errors")
    request_error_div = soup.find("div", class_="caption")

    if validation_error_div is not None:
        spinner.fail("Login failed!")
        error_msg = validation_error_div.find("li").text.strip()
        print(error_msg)

        if saved_username and "Invalid" in error_msg:
            delete_choice = input("Delete saved credentials? [y/N] ").lower().strip()
            if delete_choice.startswith("y"):
                try:
                    keyring.delete_password(SERVICE_NAME, saved_username)
                    config.pop("username", None)
                    config["save_credentials"] = False
                    with open(config_file, "w") as f:
                        f.write(json.dumps(config, indent=2))
                    print("✓ Saved credentials removed")
                except Exception as e:
                    print(f"✗ Error removing credentials: {e}")
        exit(1)
    elif request_error_div is not None:
        spinner.fail("Login failed!")
        print(request_error_div.text.strip())
        exit(1)
    else:
        spinner.succeed("Login successful!")

with Halo(text='Fetching grades...', spinner='dots') as spinner:
    r = s.get(f'https://{hac_url}/HomeAccess/Content/Student/Assignments.aspx')
    spinner.succeed("Grades loaded!")

print()

soup = BeautifulSoup(r.text, "lxml")

def clean_assignment_name(name:str) -> str:
    x = name
    x = x.replace("&quot;", "\"")
    x = x.replace("&amp;", "&")
    x = x.replace("&#39;", "'")
    if len(x) >= 41:
        x = x[:38] + "..."
    return x

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
        assignment_name = clean_assignment_name(cells[2].text.strip().splitlines()[0])
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