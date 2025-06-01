# Mangarr plugin template

You can use this plugin template for creating your own plugin.

Feel free to use anything you want but make sure that the example methods returns their specified types otherwise they will not work as intended.

Mangarr expects some keys in the its dictionaries at minimum so use the ***METHOD_NAME*_dict()** but you can add anything if you need it it will be used in arguments later on.

## Available libraries:

- [requests](https://pypi.org/project/requests/)
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
- [lxml](https://pypi.org/project/lxml/)
- [selenium](https://pypi.org/project/selenium/) (predefined in base class as *driver* with method **close_driver** that will close all driver tabs except one to avoid huge HW usage so use after being done with driver)
