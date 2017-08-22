# Copyright 2017 Google Inc.
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

"""Google Cloud Translation API wrapper."""


from google.cloud.translate_v2 import __version__
from google.cloud.translate_v2.client import Client

# These constants are essentially deprecated; strings should be used instead.
# They are imported here for backwards compatibility.
from google.cloud.translate_v2.client import BASE
from google.cloud.translate_v2.client import NMT


__all__ = (
    '__version__',
    'BASE',
    'Client',
    'NMT',
)
