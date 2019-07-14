"""
 Forked from: https://github.iu.edu/csci-b351-sp19/server.git
"""

import requests
import json
import os

class Canvas:
    """
    Canvas object that handles all interactions with the Canvas API. 

    Args:
        token (str):         Canvas API Authorization token
        course_id (str|int): The unqiue Canvas ID of the course.
        url (str):           The URL to the Canvas environment you're using. 
                             (For IU, we use a special proxy: https://kb.iu.edu/d/aaja#acc)

    Current features include: 
        getStudents:               Returns a list of students enrolled in the course.
        uploadFileToSubmission:    Uploads a file to be used in a submission comment during grading.
        deleteFile:                Delete an uploaded File.
        gradeAssignmentAndComment: Grades an assignment and optionally comments on it by uploading a file

    Expanding Functionality: 
       To add features, refer to the Canvas API: https://canvas.instructure.com/doc/api/index.html
       
       Since through IU we use a fancy Proxy, whenever Canvas lists an API call to use, for example,
       `/api/v1/courses`, we would only need to use our url + `/courses`. 

       Every time you open a new session to make a request to the canvas API, make sure you call the
       _setHeaders function to set the authentication token and content-type. Example:
       
       with requests.Session() as s:
           self._setHeaders(s)
           
           r = s.get(self.url + 'courses')

      The above will return a list of courses the user is enrolled in. 

    """
    
    def __init__(self,  token, course_id, url):
        self.course_id = course_id
        self.token = token
        self.url = url

        ## TODO:
        ## Add checks to make sure given arguments are valid!

    """
    ## Unimplemented method for not exceeding the rate limit

    def rate_catch(r, *args, **kwargs):
        if 'X-Rate-Limit-Remaining' not in r.headers:
            return
        if(int(r.headers['X-Rate-Limit-Remaining']) <= 1):
            time.sleep(abs((int(r.headers['X-Rate-Limit-Reset']) - int(time.time()))))
        else:
            time.sleep(abs((int(r.headers['X-Rate-Limit-Reset']) - int(time.time())) / int(r.headers['X-Rate-Limit-Remaining'])))
    """

    def _setHeaders(self, s):
         """
         This function takes a session and set the appropriate authorization headers.

         References: 
             [1] https://kb.iu.edu/d/aaja#acc
         """
         s.headers.update({'X-IU-Authorization': self.token, 'Content-Type': 'application/json'})

    def getStudents(self):
        """
        This function returns a list of students enrolled in the course. 

        Returns:
            json: A list of JSON elements representing the students in the course. 

        References:
            [1] https://canvas.instructure.com/doc/api/courses.html#method.courses.students
        """
        with requests.Session() as s:
            self._setHeaders(s)
            r = s.get(self.url + "courses/%s/students" % self.course_id)

        return r.json()

    def getStudentID(self, username):
        """
        This function takes a students username and returns their Canvas ID. If no student is found,
        the function returns -1. The student must be enrolled in the course. 

        Args:
            username (str): The username of the student
        
        Returns:
            int: The ID of the student, or -1 if the student was not found. 
        """

        students = self.getStudents()
        for student in students:
            if student["login_id"] == username:
                return student["id"]
        
        return -1

    def _prepareFileUpload(self, url, file_path):
        """
        This function tells Canvas that we are about to upload a file to the given
        assignment and user for a comment to the submission.The logic of this function
        will work for any type of file upload to the Canvas API, which the exception
        of the URL given to the post funcion of the session.

        Args:
            file_path (str):        Path to the file to upload.
            assignment_id(str|int): Unique Canvas ID for the assignment.
            student_id(str|int):    Unique Canvas ID for the student. 
    
        Returns:
            result (json): JSON object with results from API request. Will contain
                           the upload URL and key for the actual file upload. 

        References: 
            [1] https://canvas.instructure.com/doc/api/file.file_uploads.html
            [2] https://canvas.instructure.com/doc/api/submission_comments.html

        """
        
        with requests.Session() as s: 
            self._setHeaders(s) 

            ## get the file name by splitting the path into a list of items by the `/` char 
            file_name = file_path.split('/')
            file_name = file_name[len(file_name)-1]

            ## get the size, prepare parameters and make the request. 
            size = os.path.getsize(file_path)
            data = {'name': file_name, 'size': size}
            r = s.post(url, params=data) 
            
            #print(r.text)

            try:
                result = r.json()
            except:
                raise Exception("File Upload Token could not be retrieved.")

        #print(result)
        return result

    def _confirmUpload(self, file_path, prepare_result):
        """
        This function will upload the actual file to the URL given to us by canvas.

        Args:
            file_path (str):        The path of the file to upload
            prepare_results (json): The results of the prepareFileUpload method, which tells Canvas about the file

        Returns:
            json: a JSON containing information about the file upload. Most importantly, the ID of the file. 
    
        References: 
            [1]: https://canvas.instructure.com/doc/api/file.file_uploads.html

         """
    
        try: 
            data = prepare_result["upload_params"] ## contains key, size, etc. 
            upload_url = prepare_result["upload_url"] ## url we need to upload to
        except:
            raise Exception("Bad API Response on POST.")

        with requests.Session() as s:
            r = s.post(upload_url, data=data, files={'file': open(file_path, 'rb')})

        #print(r)
        #print(r.text)
        #print(upload_url)

        return r.json()
    
    # TODO : Figure out why this breaks
    def uploadFileToSubmission(self, file_path, assignment_id, student_id):
        """
        This function uploads a file to the submission comments for the given student on the given assingment. 

        Args:
            file_path (str):         The path to the file to upload
            assignment_id (str|int): The unique Canvas ID of the assignment
            student_id (str|int):    The unique Canvas ID of the student

        Returns:
            str: The ID of the file that was just uploaded to Canvas.

        References: 
            [1]: https://canvas.instructure.com/doc/api/file.file_uploads.html

        """
        url = self.url + 'courses/%s/assignments/%s/submissions/%s/comments/files' % (self.course_id, assignment_id, student_id)
        prepare_result = self._prepareFileUpload(url, file_path)
        result = self._confirmUpload(file_path, prepare_result)
        
        #print(result)

        return result['id']

    def uploadFileToFiles(self, file_path):
        url = self.url + 'courses/%s/files' % (self.course_id)
        prepare_result = self._prepareFileUpload(url, file_path)
        result = self._confirmUpload(file_path, prepare_result)
        
        #print(result)

        return result['id']

    def deleteFile(self, file_id):
        """
        This funciton deletes the file at the given ID.
        
        Args:
            file_id (str|int): The ID of the file to delete. 

        Returns:
            This function does not return anything. 

        Notes:
            [1]: https://canvas.instructure.com/doc/api/files.html#method.files.destroy
        """
        with requests.Session() as s:

            self._setHeaders(s)
            s.headers.update({'Content-Type': 'application/pdf'}) ## since the Canvas API returns the file we are deleting
            r = s.delete(self.url + 'files/%s' % (file_id))

    def gradeAssignmentAndComment(self, student_id, assignment_id, grade, comment=None, files=None):
        """
        This function grades and comments a file to a submission for the given student on the given assignment. 

        Args:
            student_id (str|int):   The unique CanvasID of the student
            assignment_id(str|int): The unique Canvas ID of the assignment
            grade (str):            The grade the student recieves for an assignment. Should be a string to include decimal results.
            files (int, optional):  A list of file IDs to upload for the comment. 

        Returns: 
            json: The result of the call to the submissions URL as returned by the Canvas API. 
 
        """
        with requests.Session() as s:

            self._setHeaders(s)
            
            data = {'comment[file_ids]': files, 'submission[posted_grade]': grade, 'comment[text_comment]': comment}
            url = self.url + 'courses/%s/assignments/%s/submissions/%s' % (self.course_id, assignment_id, student_id)
            r = s.put(url, params=data)

        return r.json()
