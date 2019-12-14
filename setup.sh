#!/usr/bin/env bash

red=`tput setaf 1`
green=`tput setaf 2`
reset=`tput sgr0`

clear

echo "                                                                                                                                              ";
echo "███╗   ███╗████████╗ ██████╗     ██╗███╗   ███╗ █████╗  ██████╗ ███████╗     ██████╗  █████╗ ████████╗██╗  ██╗███████╗██████╗ ███████╗██████╗ ";
echo "████╗ ████║╚══██╔══╝██╔════╝     ██║████╗ ████║██╔══██╗██╔════╝ ██╔════╝    ██╔════╝ ██╔══██╗╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔════╝██╔══██╗";
echo "██╔████╔██║   ██║   ██║  ███╗    ██║██╔████╔██║███████║██║  ███╗█████╗      ██║  ███╗███████║   ██║   ███████║█████╗  ██████╔╝█████╗  ██████╔╝";
echo "██║╚██╔╝██║   ██║   ██║   ██║    ██║██║╚██╔╝██║██╔══██║██║   ██║██╔══╝      ██║   ██║██╔══██║   ██║   ██╔══██║██╔══╝  ██╔══██╗██╔══╝  ██╔══██╗";
echo "██║ ╚═╝ ██║   ██║   ╚██████╔╝    ██║██║ ╚═╝ ██║██║  ██║╚██████╔╝███████╗    ╚██████╔╝██║  ██║   ██║   ██║  ██║███████╗██║  ██║███████╗██║  ██║";
echo "╚═╝     ╚═╝   ╚═╝    ╚═════╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝     ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝";
echo "                                                                                                                                              ";
echo "                                                                                                                                              ";

read -r -p "We're going to check dev environment dependencies and pull some docker images (~7 Gb). Do you want to continue? [y/N] " response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]
then

	echo "\nCheck dependencies..."
	git --version >/dev/null 2>&1 || { echo >&2 "${red}I require git but it's not installed. ¯\_(ツ)_/¯  Aborting...${reset}"; exit 1; }
	docker --version >/dev/null 2>&1 || { echo >&2 "${red}I require docker but it's not installed. ¯\_(ツ)_/¯  Aborting...${reset}"; exit 1; }
	docker-compose --version >/dev/null 2>&1 || { echo >&2 "${red}I require docker-compose but it's not installed. ¯\_(ツ)_/¯  Aborting...${reset}"; exit 1; }
	make --version >/dev/null 2>&1 || { echo >&2 "${red}I require make but it's not installed. ¯\_(ツ)_/¯  Aborting...${reset}"; exit 1; }
	python --version >/dev/null 2>&1 || { echo >&2 "${red}I require python but it's not installed. ¯\_(ツ)_/¯  Aborting...${reset}"; exit 1; }
	pip --version >/dev/null 2>&1 || { echo >&2 "${red}I require pip but it's not installed. ¯\_(ツ)_/¯  Aborting...${reset}"; exit 1; }
	echo "${green}Everything ok${reset}"

	echo "\nPulling some images to speed up the work!"
	docker pull jupyter/datascience-notebook:9b06df75e445
	docker pull postgres
	echo "${green}Docker Images correctly pulled!${reset}"

	echo "${green}\n#################################################################################"
	echo "#   Congrats! your environment it's ready to develop and execute this project!  #"
	echo "#################################################################################\n${reset}"

fi
