I want to start a discussion about my company storage architecture, and some problems that I face as a result. 

I am currently a one person company and I have been using a simple folder structure to organize my files. However, as my business grows, I am finding it increasingly difficult to keep track of everything. I am considering implementing a more robust storage architecture, but I am not sure where to start.

Here is my current workflow and storage structure:
My computer has two SSD drives, 
1. c: for programs and applications
2. d: for some temporary export files, google drive sync, and downloads

Then I have a NAS (Network Attached Storage) that I use for long-term storage and backups. The NAS has a folder structure that looks like this:
1. E: Database, containg everything such as scripts, Github repo, except for assets for 3d production
2. F: Project Files, each project has its own folder, and within each project folder
3. G: Photos, this is linked to synology photo, however I also keep all my Assets for 3D productions here, such as textures, models, and reference images. These files can be quite large, and I want to make sure they are organized and easily accessible.
4. V: Videos, this is linked to synology video, I currently keep my personal videos here for entertainment mostly
5. W: This is link to my synology website where I can host my personal website and portfolio. But it is not actively used at the moment.

There are also 3 cloud solutions I use.
1. Github for code and version control. I am still learning how to use it effectively, but I want to make sure my code is backed up and organized. I also want to make use of it to share project status with clients and collaborators. Not yet implemented but I am planning to use it for project management and documentation as well.

2. Google Drive, under the account oscartung@real-hk.com, it is mirrored to a folder in D: drive, I currently keep all the thumbnails for my 3d assets there. The reason is that I can use google api to anaylze each image for description to give it metadata, thus easier to search through

3. Synology Drive, this I use to share files with my clients, creating a shared folder because the files I share sometimes can be quite large, and when I share it here I can just press save file in my computer and no uploading to the web is needed. I can work on large file there too. Usually the share folder is in f: drive, the project drive, I create a 'xxx-shared' folder for each project, and share that with the client. This way I can keep all the project files in one place, and the client can access it easily without needing to download large files from email or other platforms.

My workflow for a project is usually as follows:
1. send quotation, once confirm, recieve information from client
2. model accordingly in 3dsmax
3. export to unreal engine for producing renderings and animation
4. Sometimes have to send the files to fusion for additional post production work, but not always
5. publish the final output on the share folder and notify the client
6. Client comments, I go back to 3dsmax make changes, export to unreal, publish again, repeat until the project is done.
7. issue invoice, receive payment, send receipt.

Here are some issues I face now.
1. There are many thousands of assets inside g: drive, I have managed to keep them organized like this. asset A.zip, assset A.jpg. Asset A.zip is the zip containing the 3D asset with all the files, and asset A.jpg is the thumbnail for that asset. They have the same name. However the zip file is often large and the thumbnail is small in size. What I do is that I make a copy of the thumbnail but not the zip file to google drive. Then I use the thumbnail image to create the database for searching. The metadata I current keep in an excel file, not ideal. Then export the file as csv for to search in everhythingsearch by void tools. Then when I find the thumbnail I want, I can easily find the corresponding zip file in g: drive. However, this process is quite manual and time-consuming. I want to find a way to automate this process and make it more efficient.

2. There is no way to keep track of project progress currently. I tried to use a simple text file to keep track of project status, but it quickly becomes outdated and hard to maintain. I want to find a better way to manage project documentation and progress tracking. Usually a client would send brief via email, whatsapp, or zip file with instruction. I then make the change, publish it on the share folder and notify them via email or whatsapp. But nothing gets tracked. The best I am doing is that i create a incoming folder, then everytime I new instructions I create a new folder with the date and short description as the file name with the files inside. But there is no source control, no tracking.

3. 3D assets I download from many sources over the internet, some from 3Dsky, from dimensiva, from dimensions.com. They each have different naming conventions and file structures. I want to find a way to standardize the way I organize these assets so that I can easily find and use them in my projects. Also many might be duplicated, no way for me to find as some of them have random filenames. Same problem I face with textures.

4. Scripts, Notes, Password of logins, scattered everywhere. No way to keep track, don't know what I have.

5. Plugin manangement for 3dsmax is a mess too. I don't know what plugin i use, making it hard to migrate into a new version.

6. No standize way of making a quotation. Also a mess, I use a simple text editor to get the job done. But not standardized, cannot track and compare.

I might add more to this, but I want to start the discussion here first. I am looking for suggestions on how to improve my storage architecture and workflow to address these issues. I am open to using new tools and technologies, but I want to make sure that they are easy to use and integrate well with my existing setup. The current method is the one that I invented as needed, I don't think it's the standard way of doing things. I want to adopt a more industry standard way of doing things.

Please comment and make suggestions on how I can improve my storage architecture and workflow. Thank you!

okay, I want as little 3rd party apps as possible to prevent lock-in issues and    
   migration issues in the future. I want to use as much as possible the tools that I already have, such as google drive, synology drive, github, and my NAS. I just want to find a better way to organize and manage my files and projects using these tools.
1.Connector I have tried, too slow not good
2.Obsidian I have also tried, too complex, and slow, I want to use github instead of obisdian for the job. Source control I don't need github, but just want a good naming convention and folder structure. I think have discussed that before @knowledge
4. Again want to use either google password manager or github for scattered scripts, notes, password. 

7. Now I also need to organize my unreal folder structure and naming convention
take a look at F:\UE 5.6\Content\ and see if you have any suggestions on how to organize the files there. I want to make sure that the files are organized in a way that makes it easy for me to find and use them in my projects. I also want to make sure that the naming convention is consistent and easy to understand. Try to understand how i organize things there currently and come up with a new structure and naming convention that can be applied to all my projects. I want to make sure that the structure is flexible enough to accommodate different types of projects and assets, but also standardized enough to maintain consistency across all my work. can refer to @naming_convention.md for the naming convention I use for my assets in g: drive. I want to apply a similar naming convention to my unreal content as well.

#Questions for discussion:
1. I want to have an overview of my projects and their status. (for example, any outstanding issues for KIL112)
2. I want to know the category list of 3d assets I have, and how many assets I have in each category. (for example, how many chairs, tables, etc.)
3. I want to find a chair asset for a living room project, I don't know which to use, but I prefer to use one that has been used before in other projects
4. Client sent instructions via different channels, email, whatsapp mainly, how can I keep track of all the instructions and make sure I don't miss anything?
5. quotation management, how can I keep track of all the quotations I have sent, their status (accepted, rejected, pending), and the details of each quotation (client name, project name, amount, etc.)? where should these quotation live? Gh or F: drive? 
6. I currently use waveapps for manging invoices and payments, but I want to find a better way to integrate it with my storage architecture and workflow. For example, I want to be able to easily access the invoice files and payment records from my NAS or cloud storage, and also link them to the corresponding projects and quotations. Any suggestions on how to do this?


I’ll save the current todo state exactly as shown so you can switch tasks without losing it.

Updated todo list

Saved. Your todo list is now persisted with the same state:
- completed: Read full daemon file (tail)
- in-progress: Write new search_clipboard_daemon.py
- not-started: Create search_lancedb_indexer.py
- not-started: Update requirements.txt

Ready for the next task whenever you are.