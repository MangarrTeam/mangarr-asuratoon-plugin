from plugins.base import MangaPluginBase, Formats, AgeRating, Status, NO_THUMBNAIL_URL


class TemplatePlugin(MangaPluginBase):
    languages = []

    def search_manga(self, query:str, language:str=None) -> list[dict]:
        return []

    def get_manga(self, arguments:dict) -> dict:
        return {}
        
    def get_chapters(self, arguments:dict) -> list[dict]:
        return []
    
    def get_pages(self, arguments:dict) -> list[dict]:
        return []
