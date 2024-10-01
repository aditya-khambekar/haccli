# haccli
This is a simple python script for viewing grades in Home Access Center using a command line interface.

Beautiful Soup and the requests library is used to log in and scrape Home Access Center.

## Usage
- Download haccli.py
- Update hac_url to your districts Home Access Center domain (KatyISD is prefilled)
- Run the script in the command line, you can add it to your PATH if you are fancy.
- If you choose to save your password, it will be saved in a json file in your config directory (`~/.config/haccli/storedlogin.json` on Linux)

## Contribute
I have only tested this with my account on KatyISD HAC. There may be issues with scraping other instances of HAC.

Feel free to open an issue or pull request.

## Licence
[MIT](./LICENSE). You can do whatever with this script I do not care.