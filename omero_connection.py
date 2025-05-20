# -*- coding: utf-8 -*-
"""
Created on Thu May 15 15:29:18 2025

@author: simon

port:'4064'
'omero-cci-cli.gu.se'
"""

from omero.gateway import BlitzGateway


class OmeroConnection:
       
    def __init__(self, hostname, port, token):
        self._connect_to_omero(hostname, port, token)
        
    def __del__(self):
        self._close_omero_connection()
    
    def kill_session(self):
        self._close_omero_connection(True)
        
    def get_omero_connection(self):
        return self.conn

    def _connect_to_omero(self, hostname, port, token):
        self.omero_token = token

        self.conn = BlitzGateway(host=hostname, port=port)
        is_connected = self.conn.connect(token)
    
        if not is_connected:
            raise ConnectionError("Failed to connect to OMERO")

    def _close_omero_connection(self,hardClose=False):
        if self.conn:
            self.conn.close(hard=hardClose)
       
    def get_user(self):
        return self.conn.getUser()

    def get_logged_in_user_name(self):
        return self.conn.getUser().getFullName()

    def get_user_group(self):
        groups = []
        for group in self.conn.getGroupsMemberOf():
            groups.append(group.getName())
        return groups

    def getDefaultOmeroGroup(self):
        group = self.conn.getGroupFromContext()
        return group.getName()
    
    def setOmeroGroupName(self, group):
        self.conn.setGroupNameForSession(group)

    def get_user_projects(self):
        projects = {}
        my_expId = self.conn.getUser().getId()
        for project in self.conn.listProjects(my_expId):         # Initially we just load Projects
            projects.update({project.getId(): project.getName()})
            
        return projects

    def get_dataset_from_projectID(self, project_id):
        project = self.conn.getObject("Project", project_id)
        if not project:
            raise Exception(f"Project with ID {project_id} not found")

        datasets = {}
        for dataset in project.listChildren():      # lazy-loading of Datasets here
            datasets.update({dataset.getId():dataset.getName()})

        return datasets
       
    def get_images_from_datasetID(self, dataset_id):
        dataset = self.conn.getObject("Dataset", dataset_id)
        if not dataset:
            raise Exception(f"Dataset with ID {dataset_id} not found")

        images = {}
        for image in dataset.listChildren():      # lazy-loading of images here
            images.update({image.getId():image.getName()})

        return images
    
    def get_original_upload_folder(self, image_id):
        try:
            folder = dict(self.conn.getObject("Image", image_id).getAnnotation().getValue()).get('Folder', 'uploads')
        except:
            folder =  'uploads' #fallback
        return folder
    
    def get_fileset_from_imageID(self, image_id):
        #get the image object
        image = self.conn.getObject("Image", image_id)
        return image.getFileset()
    
    def get_members_of_group(self):
        colleagues = {}
        for idx in self.conn.listColleagues():
            colleagues.update({idx.getFullName(): idx.getId()})
        
        #need also the current user!!
        colleagues.update({self.get_logged_in_user_name():self.get_user().getId()})
        return colleagues
    
    def set_user(self, Id):
        self.conn.setUserId(Id)
        
    def is_connected(self):
        return self.conn.isConnected()

if __name__ == "__main__":
    Conn = OmeroConnection('omero-cci-cli.gu.se', '4064', '9222b398-095d-488e-b7fd-4d7745dd6bff')
    
    Conn.get_members_of_group().keys()
    
    
    