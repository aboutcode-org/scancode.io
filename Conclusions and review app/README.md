## Getting started

- Recommended `node js 14+` and `npm 6+`
- Install dependencies: `npm install` or `yarn install`
- Start the server: `npm run start` or `yarn start`

## About the Project
 This project can be considered as an initial approch (frontend) for few projects and issues mentioned below. 
  
 ### Projects
- [ScanCode.io: web-based automated Conclusions app and GUI review app](https://github.com/nexB/aboutcode/wiki/GSOC-2022#scancodeio-web-based-automated-conclusions-app-and-gui-review-app)

  > This project is to create a new web application in ScanCode.io to help reach conclusions on an analysis project wrt. the origin, license or vulnerabilities of a codebase
  *  Leveraging existing code is good - but using third-party codes without knowing the license is bad. Unfortunately, most of the time finding third-party codes with proper licenses and avoiding buggy, outdated or vulnerable components is complicated and tedious. Luckily, we can use ScanCode.io to know the license of third-party codes avoiding buggy, outdated or vulnerable components. Here a new web application in ScanCode.io to help reach conclusions on an analysis project with regard to the origin, license or vulnerabilities of a codebase is immensely useful for the developers. Furthermore, such a web app will save their time tremendously while providing a feature-rich UI to visualise conclusions.  


- [ScanCode Toolkit/ScanCode.io: Create GitHub SBOM creation action(s)](https://github.com/nexB/aboutcode/wiki/Project-Ideas-Create-GitHub-SBOM-action)

  > This is about to create a scan using a GitHub action, optionally also creating SPDX and CycloneDX outputs. 
  * This web app can be directly used with this project. For example, once the scanning feature using a GitHub action is implemented we will be able to directly use this app as an ‘Automated Conclusions and GUI Review App for ScanCode Github Actions Enabled Repositories’. The relevant diagram is as follows.  ![scanpipe](https://user-images.githubusercontent.com/59219626/163776735-98509856-9cfb-48a7-bb96-45d213ae3991.png)

 ### Issues
- [ISSUE #203](https://github.com/nexB/scancode.io/issues/203)
  * The UI of this web app is designed in such a way that it can be used to implement features easily to solve many of the mentioned questions. 

## What about the backend API?

To demonstrate the app UI, I created a simple backend API that uses Azure Cosmos DB as the database. Here as the projects (third-party codes to be scanned), the Github repositories are used. To store/get/update relevant data of the Github repositories in the Azure Cosmos DB the following endpoints were created.

![endpoints](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/backend_api.PNG)

Here currently in this project, the main focus is on the app frontend. Hence, you are welcome to use Mock APIs with the mentioned endpoints. You can replace the values in `.env.example` and rename it to `.env` to use the codes related to API calls. (Even though I did not comment or remove the codes related to API calls, you can change them and use them as you wish) 

## Demonstration 

### Login Page
The basic information about projects is displayed on this page. Here the basic information are created date (the date that the files were initially added / for GitHub repositories, it is the repository created date), the updated date (the date that the files were lastly modified) and the project state. Here the projects that are in the ‘Watch’ state can only be used to scan. On the other hand, the projects that are in the ‘Unwatch’ state means they are only available in the system and ready to get scanned once the user changes the state to ‘Watch’. This feature helps us to filter the projects which are only needed to be visualized using the conclusions.
![Login Page](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/all.PNG)


Here, as the default sorting criteria, the project name is used (above figure). Users can click any of the other column names to change the sorting criteria. By clicking the arrow (down or up arrow) next to the criteria, the user can change the order of sorting. For example, by clicking ‘Updated At’ the user can sort the list of projects according to the last updated time. The user can click the column name again to toggle the sorting order (below figures).
![dsc](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/desend.PNG)
![asc](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/asc.PNG)

The user can select the Rows per page of 5, 10 or 25 and easily navigate through the list forward (‘>’) and backwards(‘<’) using arrows.
![rows](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/rows%20per%20page.PNG)

When the user ads a project (or multiple projects) for the first time, the project (or multiple projects) is set to the ‘Unwatch’ state by default. Here at any time, the user can change the project state to ‘Watch’ or ‘Unwatch’ by clicking the 3 dots.

<img width="182" alt="chngeStatus" src="https://user-images.githubusercontent.com/59219626/163785164-7b8c0379-5385-4996-bc1a-647a69922e7b.PNG">

The user can find a project by typing the project name in the search box. All the possible suggestions will be available while typing the project name partially. 
![search](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/serarch.PNG)

If the typing name is not available, it will be displayed as follows 
<img width="712" alt="search_notfound" src="https://user-images.githubusercontent.com/59219626/163785534-990a584b-0f85-4097-b0f0-7f28b234306a.PNG">

The user can remove one project or multiple projects completely from the app at once by selecting them and hitting the delete button on the top right corner.
![del](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/select.PNG)

### Watching Projects Page

The projects in the ‘Watch’ state are displayed on this page. All the above mentioned features such as searching, sorting, filtering and state-changing are available on this page.
![watch](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/watch.PNG)

### Non-Watching Projects Page

The projects in the ‘Unwatch’ state are displayed on this page. All the above mentioned features such as searching, sorting, filtering and state-changing are available on this page.
![nw](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/non%20watch.PNG)

### Not Found Page
![404](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/404.PNG)

### Logout Button
![Logout](https://github.com/viradhanus/Web-based-Automated-Conclusions-App-and-GUI-Review-App---ScanCode.io/blob/main/Front%20End/UIs/logout.PNG)

### Dashboard Page
Here the widgets will be used to visualize the conclusions. Moreover, most of the widgets will be designed such that a user can interact with them and eventually update them by hand.

#### Widget Example 01
<img width="948" alt="1" src="https://user-images.githubusercontent.com/59219626/163789539-3b3d2fcf-42b9-4a33-bb7d-da0756c1fd45.PNG">

#### Widget Example 02
<img width="947" alt="2" src="https://user-images.githubusercontent.com/59219626/163789558-80e189c6-6088-4679-834d-e0e6b8adf355.PNG">

#### Widget Example 03
<img width="948" alt="3" src="https://user-images.githubusercontent.com/59219626/163789587-3cc22a53-b093-4394-9b2c-7c1737e72c6a.PNG">

#### Widget Example 04
<img width="948" alt="4" src="https://user-images.githubusercontent.com/59219626/163789603-bdc7bba7-42ed-414b-b3b4-1ac64b5f44e4.PNG">


#### Widget Example 05
<img width="945" alt="5" src="https://user-images.githubusercontent.com/59219626/163789631-c0dfee30-e808-4078-9db2-5bb3cf490c99.PNG">




