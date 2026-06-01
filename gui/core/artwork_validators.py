import os
import re

class ArtworkValidator:
    """Base class defining artwork naming conventions for media servers."""
    
    @property
    def server_name(self) -> str:
        raise NotImplementedError
        
    def matches_artwork_name(self, filename: str, expected_name: str) -> bool:
        """Checks if a filename matches an expected artwork name, including allowed numbered suffixes."""
        filename_lower = filename.lower()
        expected_lower = expected_name.lower()
        if filename_lower == expected_lower:
            return True
            
        stem, ext = os.path.splitext(expected_lower)
        exts = {'.jpg', '.jpeg', '.png', '.webp'}
        if ext not in exts:
            return False
            
        # Select suffix conventions based on media server
        server = self.server_name.lower()
        if server == "plex":
            # Plex only allows hyphenated numbers (e.g., fanart-1.jpg, but not fanart1.jpg)
            pattern = rf"^{re.escape(stem)}(?:-\d+)?\.(?:jpg|jpeg|png|webp)$"
        else:
            # Emby and Jellyfin allow both (e.g., fanart1.jpg, fanart-1.jpg)
            pattern = rf"^{re.escape(stem)}(?:[-_]\d+|\d+)?\.(?:jpg|jpeg|png|webp)$"
            
        return bool(re.match(pattern, filename_lower))

    def has_artwork_file(self, directory: str, expected_names: list[str]) -> bool:
        """Checks if a directory contains any file matching the expected artwork names."""
        if not os.path.isdir(directory):
            return False
        try:
            entries = os.listdir(directory)
        except OSError:
            return False
            
        for name in expected_names:
            if "/" in name:
                # Handle subdirectory paths (e.g., "Staffel 01/folder.jpg")
                sub_dir, sub_name = name.split("/", 1)
                if self.has_artwork_file(os.path.join(directory, sub_dir), [sub_name]):
                    return True
                continue
                
            for entry in entries:
                if self.matches_artwork_name(entry, name):
                    return True
        return False

    @property
    def supports_banners(self) -> bool:
        return True
        
    @property
    def supports_logos(self) -> bool:
        return True
        
    @property
    def supports_thumbs(self) -> bool:
        return True

    # --- Movie Artwork Conventions ---
    
    def get_movie_poster_names(self, video_filename: str) -> list[str]:
        """Returns valid filenames for a movie's poster."""
        raise NotImplementedError
        
    def get_movie_backdrop_names(self, video_filename: str) -> list[str]:
        """Returns valid filenames for a movie's fanart/backdrop."""
        raise NotImplementedError
        
    def get_movie_logo_names(self, video_filename: str) -> list[str]:
        """Returns valid filenames for a movie's logo."""
        raise NotImplementedError
        
    def get_movie_banner_names(self, video_filename: str) -> list[str]:
        """Returns valid filenames for a movie's banner."""
        raise NotImplementedError
        
    def get_movie_thumb_names(self, video_filename: str) -> list[str]:
        """Returns valid filenames for a movie's landscape thumbnail."""
        raise NotImplementedError

    # --- TV Show Artwork Conventions ---
    
    def get_series_poster_names(self) -> list[str]:
        """Returns valid filenames for a TV show's poster (placed in show root)."""
        raise NotImplementedError
        
    def get_series_backdrop_names(self) -> list[str]:
        """Returns valid filenames for a TV show's fanart/backdrop (placed in show root)."""
        raise NotImplementedError
        
    def get_series_logo_names(self) -> list[str]:
        """Returns valid filenames for a TV show's logo (placed in show root)."""
        raise NotImplementedError
        
    def get_series_banner_names(self) -> list[str]:
        """Returns valid filenames for a TV show's banner (placed in show root)."""
        raise NotImplementedError
        
    def get_season_poster_names(self, season_num: int) -> list[str]:
        """Returns valid filenames for a TV show's season poster (absolute path/relative to show root)."""
        raise NotImplementedError

    # --- Preferred Download Names ---
    
    def get_preferred_movie_poster_name(self, video_filename: str) -> str:
        return self.get_movie_poster_names(video_filename)[0]
        
    def get_preferred_movie_backdrop_name(self, video_filename: str) -> str:
        return self.get_movie_backdrop_names(video_filename)[0]
        
    def get_preferred_movie_logo_name(self, video_filename: str) -> str:
        return self.get_movie_logo_names(video_filename)[0]
        
    def get_preferred_movie_banner_name(self, video_filename: str) -> str:
        return self.get_movie_banner_names(video_filename)[0]
        
    def get_preferred_movie_thumb_name(self, video_filename: str) -> str:
        return self.get_movie_thumb_names(video_filename)[0]

    def get_preferred_series_poster_name(self) -> str:
        return self.get_series_poster_names()[0]
        
    def get_preferred_series_backdrop_name(self) -> str:
        return self.get_series_backdrop_names()[0]
        
    def get_preferred_series_logo_name(self) -> str:
        return self.get_series_logo_names()[0]
        
    def get_preferred_series_banner_name(self) -> str:
        return self.get_series_banner_names()[0]
        
    def get_preferred_season_poster_name(self, season_num: int) -> str:
        """Returns the preferred file path (relative to show root) for a season poster."""
        # By default, we use 'seasonXX.jpg' in show root as it's cleaner and works across all servers
        return f"season{str(season_num).zfill(2)}.jpg"


class EmbyArtworkValidator(ArtworkValidator):
    """Emby specific artwork naming conventions."""
    
    @property
    def server_name(self) -> str:
        return "emby"

    def get_movie_poster_names(self, video_filename: str) -> list[str]:
        # Emby prefers poster.jpg/png inside folder, but allows file-specific naming
        base, _ = os.path.splitext(video_filename)
        return [
            "poster.jpg", "poster.png", "folder.jpg", "folder.png",
            f"{base}-poster.jpg", f"{base}-poster.png"
        ]
        
    def get_movie_backdrop_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "fanart.jpg", "fanart.png", "backdrop.jpg", "backdrop.png",
            f"{base}-fanart.jpg", f"{base}-fanart.png",
            f"{base}-backdrop.jpg", f"{base}-backdrop.png"
        ]
        
    def get_movie_logo_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "logo.png", "clearlogo.png",
            f"{base}-logo.png", f"{base}-clearlogo.png"
        ]
        
    def get_movie_banner_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "banner.jpg", "banner.png",
            f"{base}-banner.jpg", f"{base}-banner.png"
        ]
        
    def get_movie_thumb_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "thumb.jpg", "thumb.png", "landscape.jpg", "landscape.png",
            f"{base}-thumb.jpg", f"{base}-thumb.png"
        ]

    def get_series_poster_names(self) -> list[str]:
        return ["poster.jpg", "poster.png", "folder.jpg", "folder.png"]
        
    def get_series_backdrop_names(self) -> list[str]:
        return ["fanart.jpg", "fanart.png", "backdrop.jpg", "backdrop.png"]
        
    def get_series_logo_names(self) -> list[str]:
        return ["logo.png", "clearlogo.png"]
        
    def get_series_banner_names(self) -> list[str]:
        return ["banner.jpg", "banner.png"]
        
    def get_season_poster_names(self, season_num: int) -> list[str]:
        s_str = str(season_num).zfill(2)
        # Emby supports 'season01.jpg' in show root, or 'folder.jpg' inside 'Staffel 01'/'Season 01'
        # Specials season number is 0
        if season_num == 0:
            return [
                "season-specials.jpg", "season-specials.png", "season00.jpg", "season00.png",
                "Specials/folder.jpg", "Specials/folder.png", "Staffel 00/folder.jpg", "Staffel 00/folder.png",
                "Season 00/folder.jpg", "Season 00/folder.png"
            ]
        return [
            f"season{s_str}.jpg", f"season{s_str}.png",
            f"Staffel {s_str}/folder.jpg", f"Staffel {s_str}/folder.png",
            f"Season {s_str}/folder.jpg", f"Season {s_str}/folder.png"
        ]


class JellyfinArtworkValidator(ArtworkValidator):
    """Jellyfin specific artwork naming conventions (very similar to Emby but prefers backdrop over fanart)."""
    
    @property
    def server_name(self) -> str:
        return "jellyfin"

    def get_movie_poster_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "poster.jpg", "poster.png", "folder.jpg", "folder.png",
            f"{base}-poster.jpg", f"{base}-poster.png"
        ]
        
    def get_movie_backdrop_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        # Jellyfin prefers 'backdrop.jpg' over 'fanart.jpg'
        return [
            "backdrop.jpg", "backdrop.png", "fanart.jpg", "fanart.png",
            f"{base}-backdrop.jpg", f"{base}-backdrop.png",
            f"{base}-fanart.jpg", f"{base}-fanart.png"
        ]
        
    def get_movie_logo_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "logo.png", "clearlogo.png",
            f"{base}-logo.png", f"{base}-clearlogo.png"
        ]
        
    def get_movie_banner_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "banner.jpg", "banner.png",
            f"{base}-banner.jpg", f"{base}-banner.png"
        ]
        
    def get_movie_thumb_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "thumb.jpg", "thumb.png",
            f"{base}-thumb.jpg", f"{base}-thumb.png"
        ]

    def get_series_poster_names(self) -> list[str]:
        return ["poster.jpg", "poster.png", "folder.jpg", "folder.png"]
        
    def get_series_backdrop_names(self) -> list[str]:
        return ["backdrop.jpg", "backdrop.png", "fanart.jpg", "fanart.png"]
        
    def get_series_logo_names(self) -> list[str]:
        return ["logo.png", "clearlogo.png"]
        
    def get_series_banner_names(self) -> list[str]:
        return ["banner.jpg", "banner.png"]
        
    def get_season_poster_names(self, season_num: int) -> list[str]:
        s_str = str(season_num).zfill(2)
        if season_num == 0:
            return [
                "season-specials.jpg", "season-specials.png", "season00.jpg", "season00.png",
                "Specials/folder.jpg", "Specials/folder.png", "Staffel 00/folder.jpg", "Staffel 00/folder.png",
                "Season 00/folder.jpg", "Season 00/folder.png"
            ]
        return [
            f"season{s_str}.jpg", f"season{s_str}.png",
            f"Staffel {s_str}/folder.jpg", f"Staffel {s_str}/folder.png",
            f"Season {s_str}/folder.jpg", f"Season {s_str}/folder.png"
        ]


class PlexArtworkValidator(ArtworkValidator):
    """Plex specific artwork naming conventions."""
    
    @property
    def server_name(self) -> str:
        return "plex"
        
    @property
    def supports_banners(self) -> bool:
        # Plex supports banners for shows but less common for movies
        return True
        
    @property
    def supports_logos(self) -> bool:
        # Plex supports logos natively with new agents
        return True

    def get_movie_poster_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        # Plex supports poster, cover, default, folder, or file-specific
        return [
            "poster.jpg", "poster.png", "folder.jpg", "folder.png",
            "cover.jpg", "cover.png", "default.jpg", "default.png",
            f"{base}-poster.jpg", f"{base}-poster.png",
            f"{base}.jpg", f"{base}.png"
        ]
        
    def get_movie_backdrop_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "fanart.jpg", "fanart.png", "background.jpg", "background.png",
            "art.jpg", "art.png", "backdrop.jpg", "backdrop.png",
            f"{base}-fanart.jpg", f"{base}-fanart.png"
        ]
        
    def get_movie_logo_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "logo.png", "clearlogo.png",
            f"{base}-logo.png", f"{base}-clearlogo.png"
        ]
        
    def get_movie_banner_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "banner.jpg", "banner.png",
            f"{base}-banner.jpg", f"{base}-banner.png"
        ]
        
    def get_movie_thumb_names(self, video_filename: str) -> list[str]:
        base, _ = os.path.splitext(video_filename)
        return [
            "thumb.jpg", "thumb.png",
            f"{base}-thumb.jpg", f"{base}-thumb.png"
        ]

    def get_series_poster_names(self) -> list[str]:
        return ["poster.jpg", "poster.png", "folder.jpg", "folder.png", "show.jpg", "show.png"]
        
    def get_series_backdrop_names(self) -> list[str]:
        return ["fanart.jpg", "fanart.png", "background.jpg", "background.png", "art.jpg", "art.png", "backdrop.jpg", "backdrop.png"]
        
    def get_series_logo_names(self) -> list[str]:
        return ["logo.png", "clearlogo.png"]
        
    def get_series_banner_names(self) -> list[str]:
        return ["banner.jpg", "banner.png"]
        
    def get_season_poster_names(self, season_num: int) -> list[str]:
        s_str = str(season_num).zfill(2)
        if season_num == 0:
            return [
                "season-specials.jpg", "season-specials.png", "season00.jpg", "season00.png",
                "Specials/folder.jpg", "Specials/folder.png", "Staffel 00/folder.jpg", "Staffel 00/folder.png",
                "Season 00/folder.jpg", "Season 00/folder.png"
            ]
        # Plex expects seasonXX.jpg in the show folder, or folder.jpg inside the season folder
        return [
            f"season{s_str}.jpg", f"season{s_str}.png",
            f"Staffel {s_str}/folder.jpg", f"Staffel {s_str}/folder.png",
            f"Season {s_str}/folder.jpg", f"Season {s_str}/folder.png"
        ]


def get_validator(server_name: str) -> ArtworkValidator:
    """Factory to get the correct validator strategy."""
    name = (server_name or "emby").strip().lower()
    if name == "plex":
        return PlexArtworkValidator()
    elif name == "jellyfin":
        return JellyfinArtworkValidator()
    else:
        return EmbyArtworkValidator()
