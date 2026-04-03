from ProfileManager import ProfileManager

pm = ProfileManager()
pm.create_profile("Arnie")

print(pm.get_all_profiles())
print(pm.get_profile("Arnie"))