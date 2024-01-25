# naive-doc-search

A simple document search engine for my own needs.

## Get Started

1. Install all dependencies with ``requirements.txt``.

2. Write a ``config.json`` in the root directory like so:

```json

{
    "port" : 1234, // The port your service will be running on, addr will default to 0.0.0.0
    "sources" : [
        {
            "name" : "source_1",
            "source" : "../where/the/files/live/in/local",
            "extension": ["md", "markdown"], 
            "remote" : "https:///the.com/your/actual/files/are/hosted/in",
            "jekyll": true
        },
        {
            "name" : "source_2", // Name of the file source
            
            //Say you have index.html, baz/test.js, john/doe.txt live in there
            "source" : "../alpha/beta", 

            //The found files will come out as {remote}/{found_file_path}
            //Such as https:///contoso.com/foo/bar/index.html
            //https:///contoso.com/foo/bar/index.html
            //https:///contoso.com/foo/bar/baz/test.js
            "remote" : "https:///contoso.com/foo/bar", 
            "extension": ["html","js","mjs","css","md"],
            "jekyll" : false
        }
    ]
}
```

3. Run! Use ``python -m src.restful``.

4. Invoke the ``/search`` API. It accepts ``keyword`` as a string parameter (both POST and GET works). It responds like this:

```json
{
    "status": 0,
    "timestamp": "2024-01-25T23:21:07.028209",
    "content": {
        "elapsed_time": "151.68 ms",
        "matches": [
            {
                "type": "exact",
                "keyword": "KW",
                "input_keyword": "KW",
                "chunk": [
                    "this is the first line",
                    "second line",
                    "third_line",
                    "KW!",
                ],
                "priority": 0,
                "path": "/local/relative/path",
                "remote_path": "https:///contoso.com/foo/bar/test.js",
                "source": "source_2"
            },
            {
                "type": "bad_case",
                "keyword": "kw",
                "input_keyword": "KW",
                "chunk": [
                    "this is the first line",
                    "second line",
                    "third_line",
                    "kw?"
                ],
                "priority": 1,
                "path": "/local/relative/path",
                "remote_path": "https:///contoso.com/foo/bar/index.html",
                "source": "source_2"
            },
          
            //...
        ]
    }
}

```