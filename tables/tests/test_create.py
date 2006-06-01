""" This test unit checks object creation funtions, like openFile, createTable,
createArray or createGroup.
It also checks:
- name identifiers in tree objects
- title character limit for objects (255)
- limit in number in table fields (255)
"""

import sys
import unittest
import os
import re
import tempfile
import warnings

from tables import *
# important objects to test
from tables import File, Group, Leaf, Table, Array

from common import verbose, heavy, cleanup
# To delete the internal attributes automagically
unittest.TestCase.tearDown = cleanup

class Record(IsDescription):
    var1 = StringCol(length=4)     # 4-character String
    var2 = IntCol()                # integer
    var3 = Int16Col()              # short integer
    var4 = FloatCol()              # double (double-precision)
    var5 = Float32Col()            # float  (single-precision)

class createTestCase(unittest.TestCase):
    file  = "test.h5"
    title = "This is the table title"
    expectedrows = 100
    maxshort = 2 ** 15
    maxint   = 2147483648   # (2 ** 31)
    compress = 0


    def setUp(self):
        # Create an instance of HDF5 Table
        self.fileh = openFile(self.file, mode = "w")
        self.root = self.fileh.root

        # Create a table object
        self.table = self.fileh.createTable(self.root, 'atable',
                                            Record, "Table title")
        # Create an array object
        self.array = self.fileh.createArray(self.root, 'anarray',
                                            [1], "Array title")
        # Create a group object
        self.group = self.fileh.createGroup(self.root, 'agroup',
                                            "Group title")

    def tearDown(self):

        self.fileh.close()
        os.remove(self.file)
        cleanup(self)

    #----------------------------------------

    def test00_isClass(self):
        """Testing table creation"""
        assert isinstance(self.table, Table)
        assert isinstance(self.array, Array)
        assert isinstance(self.array, Leaf)
        assert isinstance(self.group, Group)

    def test01_overwriteNode(self):
        """Checking protection against node overwriting"""

        try:
            self.array = self.fileh.createArray(self.root, 'anarray',
                                                [1], "Array title")
        except NodeError:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next NameError was catched!"
                print value
        else:
            self.fail("expected a NodeError")

    def test02_syntaxname(self):
        """Checking syntax in object tree names"""

        # Now, try to attach an array to the object tree with
        # a not allowed Python variable name
        warnings.filterwarnings("error", category=NaturalNameWarning)
        try:
            self.array = self.fileh.createArray(self.root, ' array',
                                                [1], "Array title")
        except NaturalNameWarning:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next NaturalNameWarning was catched!"
                print value
        else:
            self.fail("expected a NaturalNameWarning")

        # another name error
        try:
            self.array = self.fileh.createArray(self.root, '$array',
                                                [1], "Array title")
        except NaturalNameWarning:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next NaturalNameWarning was catched!"
                print value
        else:
            self.fail("expected a NaturalNameWarning")

        # Finally, test a reserved word
        try:
            self.array = self.fileh.createArray(self.root, 'for',
                                                [1], "Array title")
        except NaturalNameWarning:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next NaturalNameWarning was catched!"
                print value
        else:
            self.fail("expected a NaturalNameWarning")
        # Reset the warning
        warnings.filterwarnings("default", category=NaturalNameWarning)

    def test03a_titleAttr(self):
        """Checking the self.title attr in nodes"""

        # Close the opened file to destroy the object tree
        self.fileh.close()
        # Open the file again to re-create the objects
        self.fileh = openFile(self.file,"r")

        # Now, test that self.title exists and is correct in all the nodes
        assert self.fileh.root.agroup._v_title == "Group title"
        assert self.fileh.root.atable.title == "Table title"
        assert self.fileh.root.anarray.title == "Array title"

    def test03b_titleLength(self):
        """Checking large title character length limit (1023)"""

        titlelength = 1023
        # Try to put a very long title on a group object
        group = self.fileh.createGroup(self.root, 'group',
                                       "t" * titlelength)
        assert group._v_title == "t" * titlelength
        assert group._f_getAttr('TITLE') == "t" * titlelength

        # Now, try with a table object
        table = self.fileh.createTable(self.root, 'table',
                                       Record, "t" * titlelength)
        assert table.title == "t" * titlelength
        assert table.getAttr("TITLE") == "t" * titlelength

        # Finally, try with an Array object
        arr = self.fileh.createArray(self.root, 'arr',
                                     [1], "t" * titlelength)
        assert arr.title == "t" * titlelength
        assert arr.getAttr("TITLE") == "t" * titlelength

    def test04_maxFields(self):
        "Checking a large number of fields (257) in tables"

        # The number of fields for a table
        #varnumber = 256
        varnumber = 257

        varnames = []
        for i in range(varnumber):
            varnames.append('int%d' % i)

        # Build a dictionary with the types as values and varnames as keys
        recordDict = {}
        i = 0
        for varname in varnames:
            recordDict[varname] = Col("Int32", 1, pos=i)
            i += 1
        # Append this entry to indicate the alignment!
        recordDict['_v_align'] = "="
        table = self.fileh.createTable(self.root, 'table',
                                       recordDict, "MetaRecord instance")
        row = table.row
        listrows = []
        # Write 10 records
        for j in range(10):
            rowlist = []
            for i in range(len(table.cols)):
                row[varnames[i]] = i*j
                rowlist.append(i*j)

            row.append()
            listrows.append(tuple(rowlist))

        # write data on disk
        table.flush()

        # Read all the data as a list
        listout = table.read(flavor="python")

        # Compare the input rowlist and output row list. They should
        # be equal.
        if verbose:
            print "Original row list:", listrows[-1]
            print "Retrieved row list:", listout[-1]
        assert listrows == listout

    # The next limitation has been released. A warning is still there, though
    def test05_maxFieldsExceeded(self):
        "Checking an excess (1025) of the maximum number of fields in tables"

        # The number of fields for a table
        varnumber = 1025

        varnames = []
        for i in range(varnumber):
            varnames.append('int%d' % i)

        # Build a dictionary with the types as values and varnames as keys
        recordDict = {}
        i = 0
        for varname in varnames:
            recordDict[varname] = Col("Int32", 1)
            i += 1

        # Now, create a table with this record object
        # This way of creating node objects has been deprecated
        #table = Table(recordDict, "MetaRecord instance")

        # Attach the table to object tree
        warnings.filterwarnings("error", category=PerformanceWarning)
        # Here, a PerformanceWarning should be raised!
        try:
            table = self.fileh.createTable(self.root, 'table',
                                           recordDict, "MetaRecord instance")
        except PerformanceWarning:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next PerformanceWarning was catched!"
                print value
        else:
            self.fail("expected an PerformanceWarning")
        # Reset the warning
        warnings.filterwarnings("default", category=PerformanceWarning)

    # The next limitation has been released
    def _test06_maxColumnNameLengthExceeded(self):
        "Checking an excess (256) of the maximum length in column names"

        # Build a dictionary with the types as values and varnames as keys
        recordDict = {}
        recordDict["a"*255] = IntCol(1)
        recordDict["b"*256] = IntCol(1) # Should trigger a ValueError

        # Now, create a table with this record object
        # This way of creating node objects has been deprecated
        table = Table(recordDict, "MetaRecord instance")

        # Attach the table to object tree
        # Here, ValueError should be raised!
        try:
            table = self.fileh.createTable(self.root, 'table',
                                           recordDict, "MetaRecord instance")
        except ValueError:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next ValueError was catched!"
                print value
        else:
            self.fail("expected an ValueError")

    def test06_noMaxColumnNameLength(self):
        "Checking unlimited length in column names"

        # Build a dictionary with the types as values and varnames as keys
        recordDict = {}
        recordDict["a"*255] = IntCol(1, pos=0)
        recordDict["b"*1024] = IntCol(1, pos=1) # Should work well

        # Attach the table to object tree
        # Here, IndexError should be raised!
        table = self.fileh.createTable(self.root, 'table',
                                       recordDict, "MetaRecord instance")
        assert table.colnames[0] == "a"*255
        assert table.colnames[1] == "b"*1024

class createAttrTestCase(unittest.TestCase):
    file  = "test.h5"
    title = "This is the table title"
    expectedrows = 100
    maxshort = 2 ** 15
    maxint   = 2147483648   # (2 ** 31)
    compress = 0

    def setUp(self):
        # Create an instance of HDF5 Table
        self.fileh = openFile(self.file, mode = "w")
        self.root = self.fileh.root

        # Create a table object
        self.table = self.fileh.createTable(self.root, 'atable',
                                            Record, "Table title")
        # Create an array object
        self.array = self.fileh.createArray(self.root, 'anarray',
                                            [1], "Array title")
        # Create a group object
        self.group = self.fileh.createGroup(self.root, 'agroup',
                                            "Group title")

    def tearDown(self):
        self.fileh.close()
        os.remove(self.file)
        cleanup(self)

#---------------------------------------

    def test01_setAttributes(self):
        """Checking setting large string attributes (File methods)"""

        attrlength = 2048
        # Try to put a long string attribute on a group object
        attr = self.fileh.setNodeAttr(self.root.agroup,
                                      "attr1", "p" * attrlength)
        # Now, try with a Table object
        attr = self.fileh.setNodeAttr(self.root.atable,
                                      "attr1", "a" * attrlength)
        # Finally, try with an Array object
        attr = self.fileh.setNodeAttr(self.root.anarray,
                                      "attr1", "n" * attrlength)

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.fileh.getNodeAttr(self.root.agroup, 'attr1') == \
               "p" * attrlength
        assert self.fileh.getNodeAttr(self.root.atable, 'attr1') == \
               "a" * attrlength
        assert self.fileh.getNodeAttr(self.root.anarray, 'attr1') == \
               "n" * attrlength

    def test02_setAttributes(self):
        """Checking setting large string attributes (Node methods)"""

        attrlength = 2048
        # Try to put a long string attribute on a group object
        self.root.agroup._f_setAttr('attr1', "p" * attrlength)
        # Now, try with a Table object
        self.root.atable.setAttr('attr1', "a" * attrlength)

        # Finally, try with an Array object
        self.root.anarray.setAttr('attr1', "n" * attrlength)

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.root.agroup._f_getAttr('attr1') == "p" * attrlength
        assert self.root.atable.getAttr("attr1") == "a" * attrlength
        assert self.root.anarray.getAttr("attr1") == "n" * attrlength


    def test03_setAttributes(self):
        """Checking setting large string attributes (AttributeSet methods)"""

        attrlength = 2048
        # Try to put a long string attribute on a group object
        self.group._v_attrs.attr1 = "p" * attrlength
        # Now, try with a Table object
        self.table.attrs.attr1 = "a" * attrlength
        # Finally, try with an Array object
        self.array.attrs.attr1 = "n" * attrlength

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.root.agroup._v_attrs.attr1 == "p" * attrlength
        assert self.root.atable.attrs.attr1 == "a" * attrlength
        assert self.root.anarray.attrs.attr1 == "n" * attrlength

    def test04_listAttributes(self):
        """Checking listing attributes """

        # With a Group object
        self.group._v_attrs.pq = "1"
        self.group._v_attrs.qr = "2"
        self.group._v_attrs.rs = "3"
        if verbose:
            print "Attribute list:", self.group._v_attrs._f_list()

        # Now, try with a Table object
        self.table.attrs.a = "1"
        self.table.attrs.c = "2"
        self.table.attrs.b = "3"
        if verbose:
            print "Attribute list:", self.table.attrs._f_list()

        # Finally, try with an Array object
        self.array.attrs.k = "1"
        self.array.attrs.j = "2"
        self.array.attrs.i = "3"
        if verbose:
            print "Attribute list:", self.array.attrs._f_list()

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.root.agroup._v_attrs._f_list("user") == \
               ["pq", "qr", "rs"]
        assert self.root.agroup._v_attrs._f_list("sys") == \
               ['CLASS','FILTERS', 'TITLE', 'VERSION']
        assert self.root.agroup._v_attrs._f_list("all") == \
               ['CLASS','FILTERS', 'TITLE', 'VERSION', "pq", "qr", "rs"]

        assert self.root.atable.attrs._f_list() == ["a", "b", "c"]
        assert self.root.atable.attrs._f_list("sys") == \
               ['AUTOMATIC_INDEX', 'CLASS',
                'FIELD_0_FILL', 'FIELD_0_NAME',
                'FIELD_1_FILL', 'FIELD_1_NAME',
                'FIELD_2_FILL', 'FIELD_2_NAME',
                'FIELD_3_FILL', 'FIELD_3_NAME',
                'FIELD_4_FILL', 'FIELD_4_NAME',
                'FILTERS_INDEX', 'FLAVOR', 'NROWS',
                'REINDEX', 'TITLE', 'VERSION']
#         assert self.root.atable.attrs._f_list("readonly") == \
#                ['CLASS', 'NROWS', 'VERSION']
        assert self.root.atable.attrs._f_list("all") == \
               ['AUTOMATIC_INDEX', 'CLASS',
                'FIELD_0_FILL', 'FIELD_0_NAME',
                'FIELD_1_FILL', 'FIELD_1_NAME',
                'FIELD_2_FILL', 'FIELD_2_NAME',
                'FIELD_3_FILL', 'FIELD_3_NAME',
                'FIELD_4_FILL', 'FIELD_4_NAME',
                'FILTERS_INDEX', 'FLAVOR', 'NROWS',
                'REINDEX', 'TITLE', 'VERSION',
                "a", "b", "c"]

        assert self.root.anarray.attrs._f_list() == ["i", "j", "k"]
        assert self.root.anarray.attrs._f_list("sys") == \
               ['CLASS', 'FLAVOR', 'TITLE', 'VERSION']
        assert self.root.anarray.attrs._f_list("all") == \
               ['CLASS', 'FLAVOR', 'TITLE', 'VERSION',
                "i", "j", "k"]

    def test05_removeAttributes(self):
        """Checking removing attributes """

        # With a Group object
        self.group._v_attrs.pq = "1"
        self.group._v_attrs.qr = "2"
        self.group._v_attrs.rs = "3"
        # delete an attribute
        del self.group._v_attrs.pq

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        if verbose:
            print "Attribute list:", self.root.agroup._v_attrs._f_list()
        # Check the local attributes names
        assert self.root.agroup._v_attrs._f_list() == ["qr", "rs"]
        if verbose:
            print "Attribute list in disk:", \
                  self.root.agroup._v_attrs._f_list("all")
        # Check the disk attribute names
        assert self.root.agroup._v_attrs._f_list("all") == \
               ['CLASS', 'FILTERS', 'TITLE', 'VERSION', "qr", "rs"]

        # delete an attribute (__delattr__ method)
        del self.root.agroup._v_attrs.qr
        if verbose:
            print "Attribute list:", self.root.agroup._v_attrs._f_list()
        # Check the local attributes names
        assert self.root.agroup._v_attrs._f_list() == ["rs"]
        if verbose:
            print "Attribute list in disk:", \
                  self.root.agroup._v_attrs._g_listAttr()
        # Check the disk attribute names
        assert self.root.agroup._v_attrs._f_list("all") == \
               ['CLASS', 'FILTERS', 'TITLE', 'VERSION', "rs"]

    def test05b_removeAttributes(self):
        """Checking removing attributes (using File.delNodeAttr()) """

        # With a Group object
        self.group._v_attrs.pq = "1"
        self.group._v_attrs.qr = "2"
        self.group._v_attrs.rs = "3"
        # delete an attribute
        self.fileh.delNodeAttr(self.group, "pq")

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        if verbose:
            print "Attribute list:", self.root.agroup._v_attrs._f_list()
        # Check the local attributes names
        assert self.root.agroup._v_attrs._f_list() == ["qr", "rs"]
        if verbose:
            print "Attribute list in disk:", \
                  self.root.agroup._v_attrs._f_list("all")
        # Check the disk attribute names
        assert self.root.agroup._v_attrs._f_list("all") == \
               ['CLASS', 'FILTERS', 'TITLE', 'VERSION', "qr", "rs"]

        # delete an attribute (File.delNodeAttr method)
        self.fileh.delNodeAttr(self.root, "qr", "agroup")
        if verbose:
            print "Attribute list:", self.root.agroup._v_attrs._f_list()
        # Check the local attributes names
        assert self.root.agroup._v_attrs._f_list() == ["rs"]
        if verbose:
            print "Attribute list in disk:", \
                  self.root.agroup._v_attrs._g_listAttr()
        # Check the disk attribute names
        assert self.root.agroup._v_attrs._f_list("all") == \
               ['CLASS', 'FILTERS', 'TITLE', 'VERSION', "rs"]

    def test06_removeAttributes(self):
        """Checking removing system attributes """

        # remove a system attribute
        try:
            if verbose:
                print "System attrs:", self.group._v_attrs._v_attrnamessys
                print "local dict:", self.group._v_attrs.__dict__
            del self.group._v_attrs.CLASS
        except AttributeError:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next AttributeError was catched!"
                print value
        else:
            self.fail("expected a AttributeError")

    def test07_renameAttributes(self):
        """Checking renaming attributes """

        # With a Group object
        self.group._v_attrs.pq = "1"
        self.group._v_attrs.qr = "2"
        self.group._v_attrs.rs = "3"
        # rename an attribute
        self.group._v_attrs._f_rename("pq", "op")

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        if verbose:
            print "Attribute list:", self.root.agroup._v_attrs._f_list()
        # Check the local attributes names (alphabetically sorted)
        assert self.root.agroup._v_attrs._f_list() == ["op", "qr", "rs"]
        if verbose:
            print "Attribute list in disk:", self.root.agroup._v_attrs._f_list("all")
        # Check the disk attribute names (not sorted)
        assert self.root.agroup._v_attrs._f_list("all") == \
               ['CLASS', 'FILTERS', 'TITLE', 'VERSION', "op", "qr", "rs"]

    def test08_renameAttributes(self):
        """Checking renaming system attributes """

        # rename a system attribute
        try:
            self.group._v_attrs._f_rename("CLASS", "op")
        except AttributeError:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next AttributeError was catched!"
                print value
        else:
            self.fail("expected a AttributeError")

    def test09_setIntAttributes(self):
        """Checking setting Int attributes"""

        # With a Table object
        self.table.attrs.pq = 1
        self.table.attrs.qr = 2
        self.table.attrs.rs = 3

        # Check the results
        if verbose:
            print "pq -->", self.table.attrs.pq
            print "qr -->", self.table.attrs.qr
            print "rs -->", self.table.attrs.rs

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.root.atable.attrs.pq == 1
        assert self.root.atable.attrs.qr == 2
        assert self.root.atable.attrs.rs == 3

    # This test is commented out, because the necessary API is not
    # public
    def _test09b_setIntAttributes(self):
        """Checking setting Int (byte, short, int) attributes"""

        # With a Table object
        self.table.attrs._g_setAttrChar("pq", chr(1))
        self.table.attrs._v_attrnames.append("pq")
        self.table.attrs._v_attrnamesuser.append("pq")

        self.table.attrs._g_setAttrShort("qr", 2)
        self.table.attrs._v_attrnames.append("qr")
        self.table.attrs._v_attrnamesuser.append("qr")

        self.table.attrs._g_setAttrInt("rs", 3)
        self.table.attrs._v_attrnames.append("rs")
        self.table.attrs._v_attrnamesuser.append("rs")

        # Check the results
        if verbose:
            print "pq -->", self.table.attrs.pq
            print "qr -->", self.table.attrs.qr
            print "rs -->", self.table.attrs.rs

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.root.atable.attrs.pq == 1
        assert self.root.atable.attrs.qr == 2
        assert self.root.atable.attrs.rs == 3

    def test10_setFloatAttributes(self):
        """Checking setting Float (double) attributes"""

        # With a Table object
        self.table.attrs.pq = 1.0
        self.table.attrs.qr = 2.0
        self.table.attrs.rs = 3.0

        # Check the results
        if verbose:
            print "pq -->", self.table.attrs.pq
            print "qr -->", self.table.attrs.qr
            print "rs -->", self.table.attrs.rs

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.root.atable.attrs.pq == 1.0
        assert self.root.atable.attrs.qr == 2.0
        assert self.root.atable.attrs.rs == 3.0

    # This test is commented out, because the necessary API is not
    # public
    def _test10b_setFloatAttributes(self):
        """Checking setting Float (float) attributes"""

        # With a Table object
        self.table.attrs._g_setAttrFloat("pq", 1.0)
        self.table.attrs._v_attrnames.append("pq")
        self.table.attrs._v_attrnamesuser.append("pq")

        self.table.attrs._g_setAttrFloat("qr", 2.0)
        self.table.attrs._v_attrnames.append("qr")
        self.table.attrs._v_attrnamesuser.append("qr")

        self.table.attrs._g_setAttrFloat("rs", 3.0)
        self.table.attrs._v_attrnames.append("rs")
        self.table.attrs._v_attrnamesuser.append("rs")

        # Check the results
        if verbose:
            print "pq -->", self.table.attrs.pq
            print "qr -->", self.table.attrs.qr
            print "rs -->", self.table.attrs.rs

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.root.atable.attrs.pq == 1.0
        assert self.root.atable.attrs.qr == 2.0
        assert self.root.atable.attrs.rs == 3.0

    def test11_setObjectAttributes(self):
        """Checking setting Object attributes"""

        # With a Table object
        self.table.attrs.pq = [1.0, 2]
        self.table.attrs.qr = (1,2)
        self.table.attrs.rs = {"ddf":32.1, "dsd":1}

        # Check the results
        if verbose:
            print "pq -->", self.table.attrs.pq
            print "qr -->", self.table.attrs.qr
            print "rs -->", self.table.attrs.rs

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        assert self.root.atable.attrs.pq == [1.0, 2]
        assert self.root.atable.attrs.qr == (1,2)
        assert self.root.atable.attrs.rs == {"ddf":32.1, "dsd":1}

    def test12_overwriteAttributes(self):
        """Checking overwriting attributes """

        # With a Group object
        self.group._v_attrs.pq = "1"
        self.group._v_attrs.qr = "2"
        self.group._v_attrs.rs = "3"
        # overwrite attributes
        self.group._v_attrs.pq = "4"
        self.group._v_attrs.qr = 2
        self.group._v_attrs.rs = [1,2,3]

        if self.close:
            if verbose:
                print "(closing file version)"
            self.fileh.close()
            self.fileh = openFile(self.file, mode = "r+")
            self.root = self.fileh.root

        if verbose:
            print "Value of Attribute pq:", self.root.agroup._v_attrs.pq
        # Check the local attributes names (alphabetically sorted)
        assert self.root.agroup._v_attrs.pq == "4"
        assert self.root.agroup._v_attrs.qr == 2
        assert self.root.agroup._v_attrs.rs == [1,2,3]
        if verbose:
            print "Attribute list in disk:", \
                  self.root.agroup._v_attrs._f_list("all")
        # Check the disk attribute names (not sorted)
        assert self.root.agroup._v_attrs._f_list("all") == \
               ['CLASS', 'FILTERS', 'TITLE', 'VERSION', "pq", "qr", "rs"]


class createAttrNotCloseTestCase(createAttrTestCase):
    close = 0

class createAttrCloseTestCase(createAttrTestCase):
    close = 1

class Record2(IsDescription):
    var1 = StringCol(length=4)    # 4-character String
    var2 = IntCol()               # integer
    var3 = Int16Col()             # short integer

class FiltersTreeTestCase(unittest.TestCase):
    title = "A title"
    nrows = 10

    def setUp(self):
        # Create a temporary file
        self.file = tempfile.mktemp(".h5")
        # Create an instance of HDF5 Table
        self.h5file = openFile(self.file, "w", filters=self.filters)
        self.populateFile()

    def populateFile(self):
        group = self.h5file.root
        # Create a tree with three levels of depth
        for j in range(5):
            # Create a table
            table = self.h5file.createTable(group, 'table1', Record2,
                                        title = self.title,
                                        filters = None)
            # Get the record object associated with the new table
            d = table.row
            # Fill the table
            for i in xrange(self.nrows):
                d['var1'] = '%04d' % (self.nrows - i)
                d['var2'] = i
                d['var3'] = i * 2
                d.append()      # This injects the Record values
            # Flush the buffer for this table
            table.flush()

            # Create a couple of arrays in each group
            var1List = [ x['var1'] for x in table.iterrows() ]
            var3List = [ x['var3'] for x in table.iterrows() ]

            self.h5file.createArray(group, 'array1', var1List, "col 1")
            self.h5file.createArray(group, 'array2', var3List, "col 3")

            # Create a couple of EArrays as well
            ea1 = self.h5file.createEArray(group, 'earray1',
                                           StringAtom(shape=(0,), length=4),
                                           "col 1")
            ea2 = self.h5file.createEArray(group, 'earray2',
                                           Int16Atom(shape=(0,)), "col 3")
            # And fill them with some values
            ea1.append(var1List)
            ea2.append(var3List)

            # Create a new group (descendant of group)
            if j == 1: # The second level
                group2 = self.h5file.createGroup(group, 'group'+str(j),
                                                 filters=self.gfilters)
            elif j == 2: # third level
                group2 = self.h5file.createGroup(group, 'group'+str(j))
            else:   # The rest of levels
                group2 = self.h5file.createGroup(group, 'group'+str(j),
                                                 filters=self.filters)
            # Iterate over this new group (group2)
            group = group2

    def tearDown(self):
        # Close the file
        if self.h5file.isopen:
            self.h5file.close()

        os.remove(self.file)
        cleanup(self)

    #----------------------------------------

    def test00_checkFilters(self):
        "Checking inheritance of filters on trees (open file version)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_checkFilters..." % self.__class__.__name__

        # First level check
        if verbose:
            print "Test filter:", repr(self.filters)
            print "Filters in file:", repr(self.h5file.filters)

        if self.filters == None:
            filters = Filters()
        else:
            filters = self.filters
        assert repr(filters) == repr(self.h5file.filters)
        # The next nodes have to have the same filter properties as
        # self.filters
        nodelist = ['/table1', '/group0/earray1', '/group0']
        for node in nodelist:
            object = self.h5file.getNode(node)
            if isinstance(object, Group):
                assert repr(filters) == repr(object._v_filters)
            else:
                assert repr(filters) == repr(object.filters)

        # Second and third level check
        group1 = self.h5file.root.group0.group1
        if self.gfilters == None:
            if self.filters == None:
                gfilters = Filters()
            else:
                gfilters = self.filters
        else:
            gfilters = self.gfilters
        if verbose:
            print "Test gfilter:", repr(gfilters)
            print "Filters in file:", repr(group1._v_filters)

        assert repr(gfilters) == repr(group1._v_filters)
        # The next nodes have to have the same filter properties as
        # gfilters
        nodelist = ['/group0/group1', '/group0/group1/earray1',
                    '/group0/group1/table1', '/group0/group1/group2/table1']
        for node in nodelist:
            object = self.h5file.getNode(node)
            if isinstance(object, Group):
                assert repr(gfilters) == repr(object._v_filters)
            else:
                assert repr(gfilters) == repr(object.filters)

        # Fourth and fifth level check
        if self.filters == None:
            # If None, the filters are inherited!
            if self.gfilters == None:
                filters = Filters()
            else:
                filters = self.gfilters
        else:
            filters = self.filters
        group3 = self.h5file.root.group0.group1.group2.group3
        if verbose:
            print "Test filter:", repr(filters)
            print "Filters in file:", repr(group3._v_filters)

        assert repr(filters) == repr(group3._v_filters)
        # The next nodes have to have the same filter properties as
        # self.filter
        nodelist = ['/group0/group1/group2/group3',
                    '/group0/group1/group2/group3/earray1',
                    '/group0/group1/group2/group3/table1',
                    '/group0/group1/group2/group3/group4']
        for node in nodelist:
            object = self.h5file.getNode(node)
            if isinstance(object, Group):
                assert repr(filters) == repr(object._v_filters)
            else:
                assert repr(filters) == repr(object.filters)


        # Checking the special case for Arrays in which the compression
        # should always be the empty Filter()
        # The next nodes have to have the same filter properties as
        # Filter()
        nodelist = ['/array1',
                    '/group0/array1',
                    '/group0/group1/array1',
                    '/group0/group1/group2/array1',
                    '/group0/group1/group2/group3/array1']
        for node in nodelist:
            object = self.h5file.getNode(node)
            assert repr(Filters()) == repr(object.filters)

    def test01_checkFilters(self):
        "Checking inheritance of filters on trees (close file version)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_checkFilters..." % self.__class__.__name__

        # Close the file
        self.h5file.close()
        # And open it again
        self.h5file = openFile(self.file, "r")

        # First level check
        if self.filters == None:
            filters = Filters()
        else:
            filters = self.filters
        if verbose:
            print "Test filter:", repr(filters)
            print "Filters in file:", repr(self.h5file.filters)

        assert repr(filters) == repr(self.h5file.filters)
        # The next nodes have to have the same filter properties as
        # self.filters
        nodelist = ['/table1', '/group0/earray1', '/group0']
        for node in nodelist:
            object = self.h5file.getNode(node)
            if isinstance(object, Group):
                assert repr(filters) == repr(object._v_filters)
            else:
                assert repr(filters) == repr(object.filters)

        # Second and third level check
        group1 = self.h5file.root.group0.group1
        if self.gfilters == None:
            if self.filters == None:
                gfilters = Filters()
            else:
                gfilters = self.filters
        else:
            gfilters = self.gfilters
        if verbose:
            print "Test filter:", repr(gfilters)
            print "Filters in file:", repr(group1._v_filters)

        repr(gfilters) == repr(group1._v_filters)
        # The next nodes have to have the same filter properties as
        # gfilters
        nodelist = ['/group0/group1', '/group0/group1/earray1',
                    '/group0/group1/table1', '/group0/group1/group2/table1']
        for node in nodelist:
            object = self.h5file.getNode(node)
            if isinstance(object, Group):
                assert repr(gfilters) == repr(object._v_filters)
            else:
                assert repr(gfilters) == repr(object.filters)

        # Fourth and fifth level check
        if self.filters == None:
            if self.gfilters == None:
                filters = Filters()
            else:
                filters = self.gfilters
        else:
            filters = self.filters
        group3 = self.h5file.root.group0.group1.group2.group3
        if verbose:
            print "Test filter:", repr(filters)
            print "Filters in file:", repr(group3._v_filters)

        repr(filters) == repr(group3._v_filters)
        # The next nodes have to have the same filter properties as
        # self.filters
        nodelist = ['/group0/group1/group2/group3',
                    '/group0/group1/group2/group3/earray1',
                    '/group0/group1/group2/group3/table1',
                    '/group0/group1/group2/group3/group4']
        for node in nodelist:
            object = self.h5file.getNode(node)
            if isinstance(object, Group):
                assert repr(filters) == repr(object._v_filters)
            else:
                assert repr(filters) == repr(object.filters)

        # Checking the special case for Arrays in which the compression
        # should always be the empty Filter()
        # The next nodes have to have the same filter properties as
        # Filter()
        nodelist = ['/array1',
                    '/group0/array1',
                    '/group0/group1/array1',
                    '/group0/group1/group2/array1',
                    '/group0/group1/group2/group3/array1']
        for node in nodelist:
            object = self.h5file.getNode(node)
            assert repr(Filters()) == repr(object.filters)


class FiltersCase1(FiltersTreeTestCase):
    filters = Filters()
    gfilters = Filters(complevel=1)

class FiltersCase2(FiltersTreeTestCase):
    filters = Filters(complevel=1, complib="bzip2")
    gfilters = Filters(complevel=1)

class FiltersCase3(FiltersTreeTestCase):
    filters = Filters(shuffle=1, complib="zlib")
    gfilters = Filters(complevel=1, shuffle=0, complib="lzo")

class FiltersCase4(FiltersTreeTestCase):
    filters = Filters(shuffle=1)
    gfilters = Filters(complevel=1, shuffle=0)

class FiltersCase5(FiltersTreeTestCase):
    filters = Filters(fletcher32=1)
    gfilters = Filters(complevel=1, shuffle=0)

class FiltersCase6(FiltersTreeTestCase):
    filters = None
    gfilters = Filters(complevel=1, shuffle=0)

class FiltersCase7(FiltersTreeTestCase):
    filters = Filters(complevel=1)
    gfilters = None

class FiltersCase8(FiltersTreeTestCase):
    filters = None
    gfilters = None

class FiltersCase9(FiltersTreeTestCase):
    filters = Filters(shuffle=1, complib="zlib")
    gfilters = Filters(complevel=5, shuffle=1, complib="bzip2")

class CopyGroupTestCase(unittest.TestCase):
    title = "A title"
    nrows = 10

    def setUp(self):
        # Create a temporary file
        self.file = tempfile.mktemp(".h5")
        self.file2 = tempfile.mktemp(".h5")
        # Create the source file
        self.h5file = openFile(self.file, "w")
        # Create the destination
        self.h5file2 = openFile(self.file2, "w")
        self.populateFile()

    def populateFile(self):
        group = self.h5file.root
        # Add some user attrs:
        group._v_attrs.attr1 = "an string for root group"
        group._v_attrs.attr2 = 124
        # Create a tree
        for j in range(5):
            for i in range(2):
                # Create a new group (brother of group)
                group2 = self.h5file.createGroup(group, 'bgroup'+str(i),
                                                 filters=None)

                # Create a table
                table = self.h5file.createTable(group2, 'table1', Record2,
                                            title = self.title,
                                            filters = None)
                # Get the record object associated with the new table
                d = table.row
                # Fill the table
                for i in xrange(self.nrows):
                    d['var1'] = '%04d' % (self.nrows - i)
                    d['var2'] = i
                    d['var3'] = i * 2
                    d.append()      # This injects the Record values
                # Flush the buffer for this table
                table.flush()

                # Add some user attrs:
                table.attrs.attr1 = "an string"
                table.attrs.attr2 = 234

                # Create a couple of arrays in each group
                var1List = [ x['var1'] for x in table.iterrows() ]
                var3List = [ x['var3'] for x in table.iterrows() ]

                self.h5file.createArray(group2, 'array1', var1List, "col 1")
                self.h5file.createArray(group2, 'array2', var3List, "col 3")

                # Create a couple of EArrays as well
                ea1 = self.h5file.createEArray(group2, 'earray1',
                                               StringAtom(shape=(0,), length=4),
                                               "col 1")
                ea2 = self.h5file.createEArray(group2, 'earray2',
                                               Int16Atom(shape=(0,)), "col 3")
                # Add some user attrs:
                ea1.attrs.attr1 = "an string for earray"
                ea2.attrs.attr2 = 123
                # And fill them with some values
                ea1.append(var1List)
                ea2.append(var3List)

            # Create a new group (descendant of group)
            group3 = self.h5file.createGroup(group, 'group'+str(j),
                                             filters=None)
            # Iterate over this new group (group3)
            group = group3
            # Add some user attrs:
            group._v_attrs.attr1 = "an string for group"
            group._v_attrs.attr2 = 124

    def tearDown(self):
        # Close the file
        if self.h5file.isopen:
            self.h5file.close()
        if self.h5file2.isopen:
            self.h5file2.close()

        os.remove(self.file)
        os.remove(self.file2)
        cleanup(self)

    #----------------------------------------

    def test00_nonRecursive(self):
        "Checking non-recursive copy of a Group"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_nonRecursive..." % self.__class__.__name__


        # Copy a group non-recursively
        srcgroup = self.h5file.root.group0.group1
#         srcgroup._f_copyChildren(self.h5file2.root,
#                                recursive=0,
#                                filters=self.filters)
        self.h5file.copyChildren(srcgroup, self.h5file2.root,
                                 recursive=0, filters=self.filters)
        if self.close:
            # Close the destination file
            self.h5file2.close()
            # And open it again
            self.h5file2 = openFile(self.file2, "r")

        # Check that the copy has been done correctly
        dstgroup = self.h5file2.root
        nodelist1 = srcgroup._v_children.keys()
        nodelist2 = dstgroup._v_children.keys()
        # Sort the lists
        nodelist1.sort(); nodelist2.sort()
        if verbose:
            print "The origin node list -->", nodelist1
            print "The copied node list -->", nodelist2
        assert srcgroup._v_nchildren == dstgroup._v_nchildren
        assert nodelist1 == nodelist2

    def test01_nonRecursiveAttrs(self):
        "Checking non-recursive copy of a Group (attributes copied)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_nonRecursiveAttrs..." % self.__class__.__name__

        # Copy a group non-recursively with attrs
        srcgroup = self.h5file.root.group0.group1
        srcgroup._f_copyChildren(self.h5file2.root,
                                 recursive=0,
                                 filters=self.filters,
                                 copyuserattrs = 1)
        if self.close:
            # Close the destination file
            self.h5file2.close()
            # And open it again
            self.h5file2 = openFile(self.file2, "r")

        # Check that the copy has been done correctly
        dstgroup = self.h5file2.root
        for srcnode in srcgroup:
            dstnode = getattr(dstgroup, srcnode._v_name)
            if isinstance(srcnode, Group):
                srcattrs = srcnode._v_attrs
                srcattrskeys = srcattrs._f_list("all")
                dstattrs = dstnode._v_attrs
                dstattrskeys = dstattrs._f_list("all")
            else:
                srcattrs = srcnode.attrs
                srcattrskeys = srcattrs._f_list("all")
                dstattrs = dstnode.attrs
                dstattrskeys = dstattrs._f_list("all")
            # These lists should already be ordered
            if verbose:
                print "srcattrskeys for node %s: %s" %(srcnode._v_name,
                                                       srcattrskeys)
                print "dstattrskeys for node %s: %s" %(dstnode._v_name,
                                                       dstattrskeys)
            assert srcattrskeys == dstattrskeys
            if verbose:
                print "The attrs names has been copied correctly"

            # Now, for the contents of attributes
            for srcattrname in srcattrskeys:
                srcattrvalue = str(getattr(srcattrs, srcattrname))
                dstattrvalue = str(getattr(dstattrs, srcattrname))
                if srcattrname == "FILTERS":
                    if self.filters == None:
                        filters = Filters()
                    else:
                        filters = self.filters
                    assert str(filters) == dstattrvalue
                else:
                    assert srcattrvalue == dstattrvalue

            if verbose:
                print "The attrs contents has been copied correctly"

    def test02_Recursive(self):
        "Checking recursive copy of a Group"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02_Recursive..." % self.__class__.__name__


        # Create the destination node
        group = self.h5file2.root
        for groupname in self.dstnode.split("/"):
            if groupname:
                group = self.h5file2.createGroup(group, groupname)
        dstgroup = self.h5file2.getNode(self.dstnode)

        # Copy a group non-recursively
        srcgroup = self.h5file.getNode(self.srcnode)
#         srcgroup._f_copyChildren(dstgroup,
#                                recursive=1,
#                                filters=self.filters)
        self.h5file.copyChildren(srcgroup, dstgroup,
                               recursive=1,
                               filters=self.filters)
        lenSrcGroup = len(srcgroup._v_pathname)
        if lenSrcGroup == 1:
            lenSrcGroup = 0  # Case where srcgroup == "/"
        if self.close:
            # Close the destination file
            self.h5file2.close()
            # And open it again
            self.h5file2 = openFile(self.file2, "r")
            dstgroup = self.h5file2.getNode(self.dstnode)

        # Check that the copy has been done correctly
        lenDstGroup = len(dstgroup._v_pathname)
        if lenDstGroup == 1:
            lenDstGroup = 0  # Case where dstgroup == "/"
        first = 1
        nodelist1 = []
        for node in srcgroup._f_walkNodes(recursive=1):
            if first:
                # skip the first group
                first = 0
                continue
            nodelist1.append(node._v_pathname[lenSrcGroup:])

        first = 1
        nodelist2 = []
        for node in dstgroup._f_walkNodes(recursive=1):
            if first:
                # skip the first group
                first = 0
                continue
            nodelist2.append(node._v_pathname[lenDstGroup:])

        if verbose:
            print "The origin node list -->", nodelist1
            print "The copied node list -->", nodelist2
        assert nodelist1 == nodelist2

    def test03_RecursiveFilters(self):
        "Checking recursive copy of a Group (cheking Filters)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03_RecursiveFilters..." % self.__class__.__name__

        # Create the destination node
        group = self.h5file2.root
        for groupname in self.dstnode.split("/"):
            if groupname:
                group = self.h5file2.createGroup(group, groupname)
        dstgroup = self.h5file2.getNode(self.dstnode)

        # Copy a group non-recursively
        srcgroup = self.h5file.getNode(self.srcnode)
        srcgroup._f_copyChildren(dstgroup,
                               recursive=1,
                               filters=self.filters)
        lenSrcGroup = len(srcgroup._v_pathname)
        if lenSrcGroup == 1:
            lenSrcGroup = 0  # Case where srcgroup == "/"
        if self.close:
            # Close the destination file
            self.h5file2.close()
            # And open it again
            self.h5file2 = openFile(self.file2, "r")
            dstgroup = self.h5file2.getNode(self.dstnode)

        # Check that the copy has been done correctly
        lenDstGroup = len(dstgroup._v_pathname)
        if lenDstGroup == 1:
            lenDstGroup = 0  # Case where dstgroup == "/"
        first = 1
        nodelist1 = {}
        for node in srcgroup._f_walkNodes(recursive=1):
            if first:
                # skip the first group
                first = 0
                continue
            nodelist1[node._v_name] = node._v_pathname[lenSrcGroup:]

        first = 1
        for node in dstgroup._f_walkNodes(recursive=1):
            if first:
                # skip the first group
                first = 0
                continue
            if isinstance(node, Group):
                repr(node._v_filters) == repr(nodelist1[node._v_name])
            else:
                repr(node.filters) == repr(nodelist1[node._v_name])


class CopyGroupCase1(CopyGroupTestCase):
    close = 0
    filters = None
    srcnode = '/group0/group1'
    dstnode = '/'

class CopyGroupCase2(CopyGroupTestCase):
    close = 1
    filters = None
    srcnode = '/group0/group1'
    dstnode = '/'

class CopyGroupCase3(CopyGroupTestCase):
    close = 0
    filters = None
    srcnode = '/group0'
    dstnode = '/group2/group3'

class CopyGroupCase4(CopyGroupTestCase):
    close = 1
    filters = Filters(complevel=1)
    srcnode = '/group0'
    dstnode = '/group2/group3'

class CopyGroupCase5(CopyGroupTestCase):
    close = 0
    filters = Filters()
    srcnode = '/'
    dstnode = '/group2/group3'

class CopyGroupCase6(CopyGroupTestCase):
    close = 1
    filters = Filters(fletcher32=1)
    srcnode = '/group0'
    dstnode = '/group2/group3'

class CopyGroupCase7(CopyGroupTestCase):
    close = 0
    filters = Filters(complevel=1, shuffle=0)
    srcnode = '/'
    dstnode = '/'

class CopyGroupCase8(CopyGroupTestCase):
    close = 1
    filters = Filters(complevel=1, complib="lzo")
    srcnode = '/'
    dstnode = '/'

class CopyFileTestCase(unittest.TestCase):
    title = "A title"
    nrows = 10

    def setUp(self):
        # Create a temporary file
        self.file = tempfile.mktemp(".h5")
        self.file2 = tempfile.mktemp(".h5")
        # Create the source file
        self.h5file = openFile(self.file, "w")
        self.populateFile()

    def populateFile(self):
        group = self.h5file.root
        # Add some user attrs:
        group._v_attrs.attr1 = "an string for root group"
        group._v_attrs.attr2 = 124
        # Create a tree
        for j in range(5):
            for i in range(2):
                # Create a new group (brother of group)
                group2 = self.h5file.createGroup(group, 'bgroup'+str(i),
                                                 filters=None)

                # Create a table
                table = self.h5file.createTable(group2, 'table1', Record2,
                                            title = self.title,
                                            filters = None)
                # Get the record object associated with the new table
                d = table.row
                # Fill the table
                for i in xrange(self.nrows):
                    d['var1'] = '%04d' % (self.nrows - i)
                    d['var2'] = i
                    d['var3'] = i * 2
                    d.append()      # This injects the Record values
                # Flush the buffer for this table
                table.flush()

                # Add some user attrs:
                table.attrs.attr1 = "an string"
                table.attrs.attr2 = 234

                # Create a couple of arrays in each group
                var1List = [ x['var1'] for x in table.iterrows() ]
                var3List = [ x['var3'] for x in table.iterrows() ]

                self.h5file.createArray(group2, 'array1', var1List, "col 1")
                self.h5file.createArray(group2, 'array2', var3List, "col 3")

                # Create a couple of EArrays as well
                ea1 = self.h5file.createEArray(group2, 'earray1',
                                               StringAtom(shape=(0,),
                                                          length=4),
                                               "col 1")
                ea2 = self.h5file.createEArray(group2, 'earray2',
                                               Int16Atom(shape=(0,)), "col 3")
                # Add some user attrs:
                ea1.attrs.attr1 = "an string for earray"
                ea2.attrs.attr2 = 123
                # And fill them with some values
                ea1.append(var1List)
                ea2.append(var3List)

            # Create a new group (descendant of group)
            group3 = self.h5file.createGroup(group, 'group'+str(j),
                                             filters=None)
            # Iterate over this new group (group3)
            group = group3
            # Add some user attrs:
            group._v_attrs.attr1 = "an string for group"
            group._v_attrs.attr2 = 124

    def tearDown(self):
        # Close the file
        if self.h5file.isopen:
            self.h5file.close()
        if self.h5file2.isopen:
            self.h5file2.close()

        os.remove(self.file)
        os.remove(self.file2)
        cleanup(self)

    #----------------------------------------

    def test00_overwrite(self):
        "Checking copy of a File (overwriting file)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_overwrite..." % self.__class__.__name__

        # Create a temporary file
        file2h = open(self.file2, "w")
        file2h.close()
        # Copy the file to the destination
        self.h5file.copyFile(self.file2, title=self.title,
                             overwrite = 1,
                             copyuserattrs = 0,
                             filters = None)

        # Close the original file, if needed
        if self.close:
            self.h5file.close()
            # re-open it
            self.h5file = openFile(self.file, "r")

        # ...and open the destination file
        self.h5file2 = openFile(self.file2, "r")

        # Check that the copy has been done correctly
        srcgroup = self.h5file.root
        dstgroup = self.h5file2.root
        nodelist1 = srcgroup._v_children.keys()
        nodelist2 = dstgroup._v_children.keys()
        # Sort the lists
        nodelist1.sort(); nodelist2.sort()
        if verbose:
            print "The origin node list -->", nodelist1
            print "The copied node list -->", nodelist2
        assert srcgroup._v_nchildren == dstgroup._v_nchildren
        assert nodelist1 == nodelist2
        assert self.h5file2.title == self.title

    def test00b_firstclass(self):
        "Checking copy of a File (first-class function)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00b_firstclass..." % self.__class__.__name__

        # Close the temporary file
        self.h5file.close()

        # Copy the file to the destination
        copyFile(self.file, self.file2, title=self.title,
                 copyuserattrs = 0, filters = None, overwrite = 1)

        # ...and open the source and destination file
        self.h5file = openFile(self.file, "r")
        self.h5file2 = openFile(self.file2, "r")

        # Check that the copy has been done correctly
        srcgroup = self.h5file.root
        dstgroup = self.h5file2.root
        nodelist1 = srcgroup._v_children.keys()
        nodelist2 = dstgroup._v_children.keys()
        # Sort the lists
        nodelist1.sort(); nodelist2.sort()
        if verbose:
            print "The origin node list -->", nodelist1
            print "The copied node list -->", nodelist2
        assert srcgroup._v_nchildren == dstgroup._v_nchildren
        assert nodelist1 == nodelist2
        assert self.h5file2.title == self.title

    def test01_copy(self):
        "Checking copy of a File (attributes not copied)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_copy..." % self.__class__.__name__

        # Copy the file to the destination
        self.h5file.copyFile(self.file2, title=self.title,
                             copyuserattrs = 0,
                             filters = self.filters)

        # Close the original file, if needed
        if self.close:
            self.h5file.close()
            # re-open it
            self.h5file = openFile(self.file, "r")

        # ...and open the destination file
        self.h5file2 = openFile(self.file2, "r")

        # Check that the copy has been done correctly
        srcgroup = self.h5file.root
        dstgroup = self.h5file2.root
        nodelist1 = srcgroup._v_children.keys()
        nodelist2 = dstgroup._v_children.keys()
        # Sort the lists
        nodelist1.sort(); nodelist2.sort()
        if verbose:
            print "The origin node list -->", nodelist1
            print "The copied node list -->", nodelist2
        assert srcgroup._v_nchildren == dstgroup._v_nchildren
        assert nodelist1 == nodelist2
        #print "_v_attrnames-->", self.h5file2.root._v_attrs._v_attrnames
        #print "--> <%s,%s>" % (self.h5file2.title, self.title)
        assert self.h5file2.title == self.title

        # Check that user attributes has not been copied
        for srcnode in srcgroup:
            dstnode = getattr(dstgroup, srcnode._v_name)
            srcattrs = srcnode._v_attrs
            srcattrskeys = srcattrs._f_list("sys")
            dstattrs = dstnode._v_attrs
            dstattrskeys = dstattrs._f_list("all")
            # These lists should already be ordered
            if verbose:
                print "srcattrskeys for node %s: %s" %(srcnode._v_name,
                                                       srcattrskeys)
                print "dstattrskeys for node %s: %s" %(dstnode._v_name,
                                                       dstattrskeys)
            assert srcattrskeys == dstattrskeys
            if verbose:
                print "The attrs names has been copied correctly"

            # Now, for the contents of attributes
            for srcattrname in srcattrskeys:
                srcattrvalue = str(getattr(srcattrs, srcattrname))
                dstattrvalue = str(getattr(dstattrs, srcattrname))
                if srcattrname == "FILTERS":
                    if self.filters == None:
                        filters = Filters()
                    else:
                        filters = self.filters
                    assert str(filters) == dstattrvalue
                else:
                    assert srcattrvalue == dstattrvalue

            if verbose:
                print "The attrs contents has been copied correctly"


    def test02_Attrs(self):
        "Checking copy of a File (attributes copied)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02_Attrs..." % self.__class__.__name__


        # Copy the file to the destination
        self.h5file.copyFile(self.file2, title=self.title,
                             copyuserattrs = 1,
                             filters = self.filters)

        # Close the original file, if needed
        if self.close:
            self.h5file.close()
            # re-open it
            self.h5file = openFile(self.file, "r")

        # ...and open the destination file
        self.h5file2 = openFile(self.file2, "r")

        # Check that the copy has been done correctly
        srcgroup = self.h5file.root
        dstgroup = self.h5file2.root
        for srcnode in srcgroup:
            dstnode = getattr(dstgroup, srcnode._v_name)
            srcattrs = srcnode._v_attrs
            srcattrskeys = srcattrs._f_list("all")
            dstattrs = dstnode._v_attrs
            dstattrskeys = dstattrs._f_list("all")
            # These lists should already be ordered
            if verbose:
                print "srcattrskeys for node %s: %s" %(srcnode._v_name,
                                                       srcattrskeys)
                print "dstattrskeys for node %s: %s" %(dstnode._v_name,
                                                       dstattrskeys)
            assert srcattrskeys == dstattrskeys
            if verbose:
                print "The attrs names has been copied correctly"

            # Now, for the contents of attributes
            for srcattrname in srcattrskeys:
                srcattrvalue = str(getattr(srcattrs, srcattrname))
                dstattrvalue = str(getattr(dstattrs, srcattrname))
                if srcattrname == "FILTERS":
                    if self.filters == None:
                        filters = Filters()
                    else:
                        filters = self.filters
                    assert str(filters) == dstattrvalue
                else:
                    assert srcattrvalue == dstattrvalue

            if verbose:
                print "The attrs contents has been copied correctly"

class CopyFileCase1(CopyFileTestCase):
    close = 0
    title = "A new title"
    filters = None

class CopyFileCase2(CopyFileTestCase):
    close = 1
    title = "A new title"
    filters = None

class CopyFileCase3(CopyFileTestCase):
    close = 0
    title = "A new title"
    filters = Filters(complevel=1)

class CopyFileCase4(CopyFileTestCase):
    close = 1
    title = "A new title"
    filters = Filters(complevel=1)

class CopyFileCase5(CopyFileTestCase):
    close = 0
    title = "A new title"
    filters = Filters(fletcher32=1)

class CopyFileCase6(CopyFileTestCase):
    close = 1
    title = "A new title"
    filters = Filters(fletcher32=1)

class CopyFileCase7(CopyFileTestCase):
    close = 0
    title = "A new title"
    filters = Filters(complevel=1, complib="lzo")

class CopyFileCase8(CopyFileTestCase):
    close = 1
    title = "A new title"
    filters = Filters(complevel=1, complib="lzo")

class CopyFileCase10(unittest.TestCase):

    def test01_notoverwrite(self):
        "Checking copy of a File (checking not overwriting)"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_notoverwrite..." % self.__class__.__name__


        # Create two empty files:
        file = tempfile.mktemp(".h5")
        fileh = openFile(file, "w")
        file2 = tempfile.mktemp(".h5")
        fileh2 = openFile(file2, "w")
        fileh2.close()  # close the second one
        # Copy the first into the second
        try:
            fileh.copyFile(file2, overwrite=0)
        except IOError:
            if verbose:
                (type, value, traceback) = sys.exc_info()
                print "\nGreat!, the next IOError was catched!"
                print value
        else:
            self.fail("expected a IOError")


        # Delete files
        fileh.close()
        os.remove(file)
        os.remove(file2)


#----------------------------------------------------------------------

def suite():
    theSuite = unittest.TestSuite()
    niter = 1
    #heavy = 1 # Uncomment this only for testing purposes!

    #theSuite.addTest(unittest.makeSuite(createAttrNotCloseTestCase))
    #theSuite.addTest(unittest.makeSuite(FiltersCase1))
    #theSuite.addTest(unittest.makeSuite(createTestCase))
    #theSuite.addTest(unittest.makeSuite(CopyGroupCase1))
    #theSuite.addTest(unittest.makeSuite(CopyGroupCase2))
    #theSuite.addTest(unittest.makeSuite(CopyFileCase1))
    for i in range(niter):
        theSuite.addTest(unittest.makeSuite(createAttrNotCloseTestCase))
        theSuite.addTest(unittest.makeSuite(createAttrCloseTestCase))
        theSuite.addTest(unittest.makeSuite(FiltersCase1))
        theSuite.addTest(unittest.makeSuite(FiltersCase2))
        theSuite.addTest(unittest.makeSuite(CopyGroupCase1))
        theSuite.addTest(unittest.makeSuite(CopyGroupCase2))
        theSuite.addTest(unittest.makeSuite(CopyFileCase1))
        theSuite.addTest(unittest.makeSuite(CopyFileCase2))
    if heavy:
        theSuite.addTest(unittest.makeSuite(createTestCase))
        theSuite.addTest(unittest.makeSuite(FiltersCase3))
        theSuite.addTest(unittest.makeSuite(FiltersCase4))
        theSuite.addTest(unittest.makeSuite(FiltersCase5))
        theSuite.addTest(unittest.makeSuite(FiltersCase6))
        theSuite.addTest(unittest.makeSuite(FiltersCase7))
        theSuite.addTest(unittest.makeSuite(FiltersCase8))
        theSuite.addTest(unittest.makeSuite(FiltersCase9))
        theSuite.addTest(unittest.makeSuite(CopyFileCase3))
        theSuite.addTest(unittest.makeSuite(CopyFileCase4))
        theSuite.addTest(unittest.makeSuite(CopyFileCase5))
        theSuite.addTest(unittest.makeSuite(CopyFileCase6))
        theSuite.addTest(unittest.makeSuite(CopyFileCase7))
        theSuite.addTest(unittest.makeSuite(CopyFileCase8))
        theSuite.addTest(unittest.makeSuite(CopyFileCase10))
        theSuite.addTest(unittest.makeSuite(CopyGroupCase3))
        theSuite.addTest(unittest.makeSuite(CopyGroupCase4))
        theSuite.addTest(unittest.makeSuite(CopyGroupCase5))
        theSuite.addTest(unittest.makeSuite(CopyGroupCase6))
        theSuite.addTest(unittest.makeSuite(CopyGroupCase7))
        theSuite.addTest(unittest.makeSuite(CopyGroupCase8))

    return theSuite


if __name__ == '__main__':
    unittest.main( defaultTest='suite' )