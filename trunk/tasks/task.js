{
    "title": "Example task",
    "author": "Anton Vakhrushev",

    "silent": false,
    
    "models": {
    
        "simpleexample": {
        
            "title": "Simple example model",

            "data": {
            
                "x": {
                    "type":     "int",
                    "default":  10
                },
                
                "u": {
                    "type":     "double",
                    "default":  3.14
                }
            },

            "methods": {
            
                "default": {
                    "title": "Default method",
                    "data": {
                        "p": {
                            "type":     "int",
                            "default":  20
                        }
                    }
                }
            },
            
            "result": {
                
                "data": {
                    "sum": "int"
                },
                
                "table": {
                    "head": [
                        { "x" : "int" },
                        { "u" : "double" }
                    ]
                }
                
            }
        }
    }
}

