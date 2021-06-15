# -*- coding: utf-8 -*-

import pytest
import sys
from .test_base_class import TestBaseClass
from aerospike import exception as e
from aerospike_helpers import expressions as exp
from .as_status_codes import AerospikeStatus

aerospike = pytest.importorskip("aerospike")
try:
    import aerospike
except:
    print("Please install aerospike python client.")
    sys.exit(1)


class TestScanPagination(TestBaseClass):

    @pytest.fixture(autouse=True)
    def setup(self, request, as_connection):
        self.test_ns = 'test'
        self.test_set = 'demo'

        self.partition_1000_count = 0
        self.partition_1001_count = 0
        self.partition_1002_count = 0
        self.partition_1003_count = 0

        as_connection.truncate(self.test_ns, None, 0)

        for i in range(1, 100000):
            put = 0
            rec_partition = as_connection.get_key_partition_id(
                self.test_ns, self.test_set, str(i))

            if rec_partition == 1000:
                self.partition_1000_count += 1
                put = 1
            if rec_partition == 1001:
                self.partition_1001_count += 1
                put = 1
            if rec_partition == 1002:
                self.partition_1002_count += 1
                put = 1
            if rec_partition == 1003:
                self.partition_1003_count += 1
                put = 1
            if put:
                rec = {
                    'i': i,
                    's': 'xyz',
                    'l': [2, 4, 8, 16, 32, None, 128, 256],
                    'm': {'partition': rec_partition, 'b': 4, 'c': 8, 'd': 16}
                }
                key = {'ns': self.test_ns, \
                       'set': self.test_set, \
                        'key': str(i), \
                        'digest': as_connection.get_key_digest(self.test_ns, self.test_set, str(i))}
                as_connection.put(key, rec)
        print(f"{self.partition_1000_count} records are put in partition 1000, \
                {self.partition_1001_count} records are put in partition 1001, \
                {self.partition_1002_count} records are put in partition 1002, \
                {self.partition_1003_count} records are put in partition 1003")

        def teardown():
            for i in range(1, 100000):
                put = 0
                key = ('test', u'demo', str(i))
                rec_partition = as_connection.get_key_partition_id(
                    self.test_ns, self.test_set, str(i))

                if rec_partition == 1000:
                    self.partition_1000_count += 1
                    put = 1
                if rec_partition == 1001:
                    self.partition_1001_count += 1
                    put = 1
                if rec_partition == 1002:
                    self.partition_1002_count += 1
                    put = 1
                if rec_partition == 1003:
                    self.partition_1003_count += 1
                    put = 1
                if put:
                    as_connection.remove(key)

        request.addfinalizer(teardown)

    def test_scan_pagination_with_existent_ns_and_set(self):

        records = []
        scan_page_size = [12]
        scan_count = [0]
        scan_pages = [5]
        max_records = self.partition_1000_count + \
            self.partition_1001_count + \
            self.partition_1002_count + \
            self.partition_1003_count
        partition_filter = {'begin': 1000, 'count': 4}
        policy = {'max_records': scan_page_size[0],
                  'partition_filter': partition_filter}

        def callback(input_tuple):
            if(input_tuple == None):
                return True #scan complete
            (_, _, record) = input_tuple
            records.append(record)
            #print(record)
            scan_count[0] = scan_count[0] + 1
            #if (scan_page_size[0] == scan_count[0]):
            #     partition_filter.update['digest'] = {'init': 1, 'value': record[0][3]}
            #     scan_pending_records -= scan_page_size[0]
            #     #return False
            return True

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        i = 0
        for i in range(scan_pages[0]):
        #while True:
            #i = i + 1
            #with pytest.raises(e.ClientError):
            scan_obj.foreach(callback, policy)
            #assert scan_page_size[0] == scan_count[0]
            scan_count[0] = 0
            if scan_obj.is_done() == True: 
                print(f"scan completed iter:{i}")
                break

        assert len(records) == ((scan_page_size[0] * scan_pages[0]) if (scan_page_size[0] * scan_pages[0]) < max_records else max_records)

    def test_scan_pagination_with_existent_ns_and_none_set(self):

        records = []

        def callback(input_tuple):
            _, _, record = input_tuple
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, None)
        scan_obj.paginate()

        scan_obj.foreach(callback, {'partition_filter': {
                         'begin': 1000, 'count': 1}})

        assert len(records) == self.partition_1000_count

    def test_scan_pagination_with_timeout_policy(self):

        ns = 'test'
        st = 'demo'

        records = []

        def callback(input_tuple):
            _, _, record = input_tuple
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        scan_obj.foreach(callback, {'timeout': 1001, 'partition_filter': {
                         'begin': 1000, 'count': 1}})

        assert len(records) == self.partition_1000_count

    # NOTE: This could fail if node record counts are small and unbalanced across nodes.
    @pytest.mark.xfail(reason="Might fail depending on record count and distribution.")
    def test_scan_pagination_with_max_records_policy(self):

        ns = 'test'
        st = 'demo'

        records = []

        max_records = self.partition_1000_count

        def callback(input_tuple):
            _, _, record = input_tuple
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        scan_obj.foreach(callback, {'max_records': max_records, 'partition_filter': {
                         'begin': 1000, 'count': 1}})
        assert len(records) == self.partition_1000_count

    def test_scan_pagination_with_all_records_policy(self):

        ns = 'test'
        st = 'demo'

        records = []

        max_records = self.partition_1000_count + \
            self.partition_1001_count + \
            self.partition_1002_count + \
            self.partition_1003_count

        def callback(input_tuple):
            _, _, record = input_tuple
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        scan_obj.foreach(callback, {'max_records': max_records, 'partition_filter': {
                         'begin': 1000, 'count': 4}})
        assert len(records) == max_records

    def test_scan_pagination_with_socket_timeout_policy(self):

        ns = 'test'
        st = 'demo'

        records = []

        def callback(input_tuple):
            _, _, record = input_tuple
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        scan_obj.foreach(callback, {'socket_timeout': 9876, 'partition_filter': {
                         'begin': 1000, 'count': 1}})

        assert len(records) == self.partition_1000_count

    def test_scan_pagination_with_records_per_second_policy(self):

        ns = 'test'
        st = 'demo'

        records = []

        def callback(input_tuple):
            _, _, record = input_tuple
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        scan_obj.foreach(callback, {'records_per_second': 10, 'partition_filter': {
                         'begin': 1000, 'count': 1}})
        assert len(records) == self.partition_1000_count

    def test_scan_pagination_with_callback_returning_false(self):
        """
            Invoke scan() with callback function returns false
        """

        records = []

        def callback(input_tuple):
            _, _, record = input_tuple
            if len(records) == 10:
                return False
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        scan_obj.foreach(callback, {'timeout': 1000, 'partition_filter': {
                         'begin': 1000, 'count': 1}})
        assert len(records) == 10

    def test_scan_pagination_with_results_method(self):

        ns = 'test'
        st = 'demo'

        scan_obj = self.as_connection.scan(ns, st)

        records = scan_obj.results(
            {'partition_filter': {'begin': 1001, 'count': 1}})
        assert len(records) == self.partition_1001_count

    def test_scan_pagination_with_multiple_foreach_on_same_scan_object(self):
        """
            Invoke multiple foreach on same scan object.
        """
        records = []

        def callback(input_tuple):
            _, _, record = input_tuple
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        scan_obj.foreach(callback, {'partition_filter': {
                         'begin': 1001, 'count': 1}})

        assert len(records) == self.partition_1001_count

        records = []
        scan_obj.foreach(callback, {'partition_filter': {
                         'begin': 1001, 'count': 1}})

        assert len(records) == 0

    def test_scan_pagination_with_multiple_results_call_on_same_scan_object(self):

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)

        records = scan_obj.results(
            {'partition_filter': {'begin': 1002, 'count': 1}})
        assert len(records) == self.partition_1002_count

        records = []
        records = scan_obj.results(
            {'partition_filter': {'begin': 1002, 'count': 1}})
        assert len(records) == self.partition_1002_count

    def test_scan_pagination_without_any_parameter(self):

        with pytest.raises(e.ParamError) as err:
            scan_obj = self.as_connection.scan()
            assert True

    def test_scan_pagination_with_non_existent_ns_and_set(self):

        ns = 'namespace'
        st = 'set'

        records = []
        scan_obj = self.as_connection.scan(ns, st)
        scan_obj.paginate()

        def callback(input_tuple):
            _, _, record = input_tuple
            records.append(record)

        with pytest.raises(e.ClientError) as err_info:
            scan_obj.foreach(callback, {'partition_filter': {
                             'begin': 1001, 'count': 1}})
        err_code = err_info.value.code
        assert err_code == AerospikeStatus.AEROSPIKE_ERR_CLIENT

    def test_scan_pagination_with_callback_contains_error(self):
        records = []

        def callback(input_tuple):
            _, _, record = input_tuple
            raise Exception("callback error")
            records.append(record)

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        with pytest.raises(e.ClientError) as err_info:
            scan_obj.foreach(callback, {'timeout': 1000, 'partition_filter': {
                             'begin': 1001, 'count': 1}})

        err_code = err_info.value.code
        assert err_code == AerospikeStatus.AEROSPIKE_ERR_CLIENT

    def test_scan_pagination_with_callback_non_callable(self):
        records = []

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        with pytest.raises(e.ClientError) as err_info:
            scan_obj.foreach(
                5, {'partition_filter': {'begin': 1001, 'count': 1}})

        err_code = err_info.value.code
        assert err_code == AerospikeStatus.AEROSPIKE_ERR_CLIENT

    def test_scan_pagination_with_callback_wrong_number_of_args(self):

        def callback():
            pass

        scan_obj = self.as_connection.scan(self.test_ns, self.test_set)
        scan_obj.paginate()

        with pytest.raises(e.ClientError) as err_info:
            scan_obj.foreach(callback, {'partition_filter': {
                             'begin': 1001, 'count': 1}})

        err_code = err_info.value.code
        assert err_code == AerospikeStatus.AEROSPIKE_ERR_CLIENT
