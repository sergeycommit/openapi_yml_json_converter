I encountered an issue when generating a client using swagger-codegen from auto-generated documentation by drf_spectacular view for a Django application.
The problems were in the type of data being passed ( | ) and in their names.
I was only able to solve it using this script.
I'm not responsible for data loss; testing is necessary (for my spec of 56,000 lines, this was impractical).
#USAGE
In the config, replace with your file names.
