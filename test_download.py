from download_service import get_movie_versions


movie_id = 961
versions = get_movie_versions(movie_id)
if versions:
    for version in versions:
        print(version)
else:
    print("No authorized versions found.")
