Forest Skin for Weewx

The Software is provided "as is" without warranty of any kind, either express or implied, including without limitation any implied warranties of condition, uninterrupted use, merchantability, fitness for a particular purpose, or non-infringement.

Feel free to tweak or change this skin as you see fit!

1. Unzip the contents of the forest.zip into /etc/weewx/skins directory
2. Change the /etc/weewx.conf file and add the following to the StdReport section:

#Forest Skin
	[[ForestReport]]
		skin = forest
		HTML_ROOT = /var/www/weewx/forest
		
3. Restart Weewx
4. You can change the header image by replacing the header.jpg image in the images folder with your own image (size should be 980x98)

Enjoy!