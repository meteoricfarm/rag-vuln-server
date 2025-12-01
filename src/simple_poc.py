from langchain_community.document_loaders import EverNoteLoader

if __name__ == "__main__":
    loader = EverNoteLoader(
        "./data/payload.xml"
    )
    print(loader.load())
