# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Define API Queries."""

import six

from google.cloud.bigquery._helpers import _TypedProperty
from google.cloud.bigquery._helpers import _rows_from_json
from google.cloud.bigquery.dataset import Dataset
from google.cloud.bigquery.job import QueryJob
from google.cloud.bigquery.table import _parse_schema_resource
from google.cloud.bigquery._helpers import _build_udf_resources
from google.cloud.bigquery._helpers import UDFResourcesProperty


class _SyncQueryConfiguration(object):
    """User-settable configuration options for synchronous query jobs.

    Values which are ``None`` -> server defaults.
    """
    _default_dataset = None
    _dry_run = None
    _max_results = None
    _timeout_ms = None
    _preserve_nulls = None
    _use_query_cache = None
    _use_legacy_sql = None


class QueryResults(object):
    """Synchronous job: query tables.

    :type query: str
    :param query: SQL query string

    :type client: :class:`google.cloud.bigquery.client.Client`
    :param client: A client which holds credentials and project configuration
                   for the dataset (which requires a project).

    :type udf_resources: tuple
    :param udf_resources: An iterable of
                        :class:`google.cloud.bigquery.job.UDFResource`
                        (empty by default)
    """

    _UDF_KEY = 'userDefinedFunctionResources'

    def __init__(self, query, client, udf_resources=()):
        self._client = client
        self._properties = {}
        self.query = query
        self._configuration = _SyncQueryConfiguration()
        self.udf_resources = udf_resources
        self._job = None

    @classmethod
    def from_query_job(cls, job):
        """Factory: construct from an existing job.

        :type job: :class:`~google.cloud.bigquery.job.QueryJob`
        :param job: existing job

        :rtype: :class:`QueryResults`
        :returns: the instance, bound to the job
        """
        instance = cls(job.query, job._client, job.udf_resources)
        instance._job = job
        job_ref = instance._properties.setdefault('jobReference', {})
        job_ref['jobId'] = job.name
        if job.default_dataset is not None:
            instance.default_dataset = job.default_dataset
        if job.use_query_cache is not None:
            instance.use_query_cache = job.use_query_cache
        if job.use_legacy_sql is not None:
            instance.use_legacy_sql = job.use_legacy_sql
        return instance

    @property
    def project(self):
        """Project bound to the job.

        :rtype: str
        :returns: the project (derived from the client).
        """
        return self._client.project

    def _require_client(self, client):
        """Check client or verify over-ride.

        :type client: :class:`~google.cloud.bigquery.client.Client` or
                      ``NoneType``
        :param client: the client to use.  If not passed, falls back to the
                       ``client`` stored on the current dataset.

        :rtype: :class:`google.cloud.bigquery.client.Client`
        :returns: The client passed in or the currently bound client.
        """
        if client is None:
            client = self._client
        return client

    @property
    def cache_hit(self):
        """Query results served from cache.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#cacheHit

        :rtype: bool or ``NoneType``
        :returns: True if the query results were served from cache (None
                  until set by the server).
        """
        return self._properties.get('cacheHit')

    @property
    def complete(self):
        """Server completed query.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#jobComplete

        :rtype: bool or ``NoneType``
        :returns: True if the query completed on the server (None
                  until set by the server).
        """
        return self._properties.get('jobComplete')

    @property
    def errors(self):
        """Errors generated by the query.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#errors

        :rtype: list of mapping, or ``NoneType``
        :returns: Mappings describing errors generated on the server (None
                  until set by the server).
        """
        return self._properties.get('errors')

    @property
    def name(self):
        """Job name, generated by the back-end.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#jobReference

        :rtype: list of mapping, or ``NoneType``
        :returns: Mappings describing errors generated on the server (None
                  until set by the server).
        """
        return self._properties.get('jobReference', {}).get('jobId')

    @property
    def job(self):
        """Job instance used to run the query.

        :rtype: :class:`google.cloud.bigquery.job.QueryJob`, or ``NoneType``
        :returns: Job instance used to run the query (None until
                  ``jobReference`` property is set by the server).
        """
        if self._job is None:
            job_ref = self._properties.get('jobReference')
            if job_ref is not None:
                self._job = QueryJob(job_ref['jobId'], self.query,
                                     self._client)
        return self._job

    @property
    def page_token(self):
        """Token for fetching next bach of results.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#pageToken

        :rtype: str, or ``NoneType``
        :returns: Token generated on the server (None until set by the server).
        """
        return self._properties.get('pageToken')

    @property
    def total_rows(self):
        """Total number of rows returned by the query.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#totalRows

        :rtype: int, or ``NoneType``
        :returns: Count generated on the server (None until set by the server).
        """
        return self._properties.get('totalRows')

    @property
    def total_bytes_processed(self):
        """Total number of bytes processed by the query.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#totalBytesProcessed

        :rtype: int, or ``NoneType``
        :returns: Count generated on the server (None until set by the server).
        """
        return self._properties.get('totalBytesProcessed')

    @property
    def rows(self):
        """Query results.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#rows

        :rtype: list of tuples of row values, or ``NoneType``
        :returns: fields describing the schema (None until set by the server).
        """
        return _rows_from_json(self._properties.get('rows', ()), self.schema)

    @property
    def schema(self):
        """Schema for query results.

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#schema

        :rtype: list of :class:`SchemaField`, or ``NoneType``
        :returns: fields describing the schema (None until set by the server).
        """
        return _parse_schema_resource(self._properties.get('schema', {}))

    default_dataset = _TypedProperty('default_dataset', Dataset)
    """See:
    https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#defaultDataset
    """

    dry_run = _TypedProperty('dry_run', bool)
    """See:
    https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#dryRun
    """

    max_results = _TypedProperty('max_results', six.integer_types)
    """See:
    https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#maxResults
    """

    preserve_nulls = _TypedProperty('preserve_nulls', bool)
    """See:
    https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#preserveNulls
    """

    timeout_ms = _TypedProperty('timeout_ms', six.integer_types)
    """See:
    https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#timeoutMs
    """

    udf_resources = UDFResourcesProperty()

    use_query_cache = _TypedProperty('use_query_cache', bool)
    """See:
    https://cloud.google.com/bigquery/docs/reference/v2/jobs/query#useQueryCache
    """

    use_legacy_sql = _TypedProperty('use_legacy_sql', bool)
    """See:
    https://cloud.google.com/bigquery/docs/\
    reference/v2/jobs/query#useLegacySql
    """

    def _set_properties(self, api_response):
        """Update properties from resource in body of ``api_response``

        :type api_response: httplib2.Response
        :param api_response: response returned from an API call
        """
        self._properties.clear()
        self._properties.update(api_response)

    def _build_resource(self):
        """Generate a resource for :meth:`begin`."""
        resource = {'query': self.query}

        if self.default_dataset is not None:
            resource['defaultDataset'] = {
                'projectId': self.project,
                'datasetId': self.default_dataset.name,
            }

        if self.max_results is not None:
            resource['maxResults'] = self.max_results

        if self.preserve_nulls is not None:
            resource['preserveNulls'] = self.preserve_nulls

        if self.timeout_ms is not None:
            resource['timeoutMs'] = self.timeout_ms

        if self.use_query_cache is not None:
            resource['useQueryCache'] = self.use_query_cache

        if self.use_legacy_sql is not None:
            resource['useLegacySql'] = self.use_legacy_sql

        if self.dry_run is not None:
            resource['dryRun'] = self.dry_run

        if len(self._udf_resources) > 0:
            resource[self._UDF_KEY] = _build_udf_resources(self._udf_resources)

        return resource

    def run(self, client=None):
        """API call:  run the query via a POST request

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/query

        :type client: :class:`~google.cloud.bigquery.client.Client` or
                      ``NoneType``
        :param client: the client to use.  If not passed, falls back to the
                       ``client`` stored on the current dataset.
        """
        if self._job is not None:
            raise ValueError("Query job is already running.")

        client = self._require_client(client)
        path = '/projects/%s/queries' % (self.project,)
        api_response = client._connection.api_request(
            method='POST', path=path, data=self._build_resource())
        self._set_properties(api_response)

    def fetch_data(self, max_results=None, page_token=None, start_index=None,
                   timeout_ms=None, client=None):
        """API call:  fetch a page of query result data via a GET request

        See:
        https://cloud.google.com/bigquery/docs/reference/v2/jobs/getQueryResults

        :type max_results: int
        :param max_results: (Optional) maximum number of rows to return.

        :type page_token: str
        :param page_token:
            (Optional) token representing a cursor into the table's rows.

        :type start_index: int
        :param start_index: (Optional) zero-based index of starting row

        :type timeout_ms: int
        :param timeout_ms:
            (Optional) timeout, in milliseconds, to wait for query to complete

        :type client: :class:`~google.cloud.bigquery.client.Client` or
                      ``NoneType``
        :param client: the client to use.  If not passed, falls back to the
                       ``client`` stored on the current dataset.

        :rtype: tuple
        :returns: ``(row_data, total_rows, page_token)``, where ``row_data``
                  is a list of tuples, one per result row, containing only
                  the values;  ``total_rows`` is a count of the total number
                  of rows in the table;  and ``page_token`` is an opaque
                  string which can be used to fetch the next batch of rows
                  (``None`` if no further batches can be fetched).
        :raises: ValueError if the query has not yet been executed.
        """
        if self.name is None:
            raise ValueError("Query not yet executed:  call 'run()'")

        client = self._require_client(client)
        params = {}

        if max_results is not None:
            params['maxResults'] = max_results

        if page_token is not None:
            params['pageToken'] = page_token

        if start_index is not None:
            params['startIndex'] = start_index

        if timeout_ms is not None:
            params['timeoutMs'] = timeout_ms

        path = '/projects/%s/queries/%s' % (self.project, self.name)
        response = client._connection.api_request(method='GET',
                                                  path=path,
                                                  query_params=params)
        self._set_properties(response)

        total_rows = response.get('totalRows')
        if total_rows is not None:
            total_rows = int(total_rows)
        page_token = response.get('pageToken')
        rows_data = _rows_from_json(response.get('rows', ()), self.schema)

        return rows_data, total_rows, page_token