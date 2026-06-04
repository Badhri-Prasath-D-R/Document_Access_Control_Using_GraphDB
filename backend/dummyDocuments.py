import pandas as pd
import faker

fake = faker.Faker()

documentID = []
documentName = []
for i in range(0,10000):
    id = i+1
    name = f"file_{id}"
    documentID.append(id)
    documentName.append(name)

data = {
    "DocumentID":documentID,
    "DocumentName":documentName
}

df = pd.DataFrame(data)

df.to_csv("documents.csv", index = False)

print("created documents.csv")
