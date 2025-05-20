# Omero download client

As simple client to download data from the Centre for Cellular Imaging, Gothenburg, Omero's server.

## Installation

### Standalone

In construction! Stay tuned!

### Python

The source code is a couple of python script, one for the user interface (gui.py) and the other one handling the Omero connection.

1. Download and install [miniforge](https://conda-forge.org/download/). 
2. Clone or download the repository
3. **Open a terminal and navigate to the folder**

   ```bash
   cd path/to/Omero_download_client-main
   ```
4. **Create and install the environment**
	
	```bash
	conda env create -f environment.yml
	```
5. **Activate the environment**

   ```bash
   conda activate omero-download-env
   ```
6. **Run Spyder** or directly `gui.py`
   ```bash
   spyder
   ```

   ```bash
   python3 gui.py
   ```
   
## Downlad images

### Login

Clicking on 'Session' --> 'Login' will open the following window.

![Login window](https://github.com/CCI-GU-Sweden/Omero_download_client/blob/main/README/login.png)

The client requires you to login on the Omero.web first, then grab the OAuth token (if such an option is enable).

You can access the correct webpage by clicking on the 'Get your token from Omero' link, or [here](https://omero-cci-users.gu.se/oauth/sessiontoken).

> [!CAUTION]
> Your token is valid only for a certain duration!

Once your are logged in, a confirmation will appear and your data will start to load. Be patient if you have few thousands of images!

The 'Settings' --> 'Configure' allow you to select the Omero server and port to connect to. This is prefilled with the CCI-Omero settings.

### Selecting the files to download

On the top, you can select the group from which you want to download the data from. Next to it, you can select from whom you want to download the data from, if the group policy is not **private**. Next to it is a refresh button in case you are modify/renaming data in the omero.web in parallel.

![Group toolbar](https://github.com/CCI-GU-Sweden/Omero_download_client/blob/main/README/group_toolbar.png)

Double clicking on a project will transfer the whole project to the download queue. In a similar way for the dataset. If on one image, only the image will be transfered.  

If the image happen to have a key-pair value called 'Folder', it will create an extra layer with the name of the folder.

For easy navigation, the items in the Omero data will be color coded:
- 🟢: The whole project/dataset will be downloaded
- 🟠: Only a part of the project/dataset will be downloaded

![Download queue](https://github.com/CCI-GU-Sweden/Omero_download_client/blob/main/README/download_queue.png)

> [!CAUTION]
> In case of multi-scene/position/Zone..., since the **original** image will be downloaded, **ALL** of them will be download as well, having only 1 of them is acceptable.

> [!CAUTION]
> The app is expecting images to be part of the following structure: project --> dataset --> image. If the structure is different, the images will not be detected!


### Download
Before downloading, be sure to select a local directory for the files destination.

Then hit 💥 the 'Download' button!

A Download progress window will appear, with 2 progress bars:
- The top one for which file is currently being downloaded versus the total amout of files to download
- The bottom one the progress of the current file being downloaded

![Progress bar](https://github.com/CCI-GU-Sweden/Omero_download_client/blob/main/README/progress_bar.png)

After the download has been completed, the download queue will be empty. Check the presence of the files.

The app does not allow you to delete files from Omero, please do it in the Omero.web interface!

Before closing the app, be sure to 'Session' --> 'Disconnect' to invalidate your token.

> [!CAUTION]
> Attachments, tags and key-pair values are **NOT** part of the image and will **NOT** be downloaded by this app!
