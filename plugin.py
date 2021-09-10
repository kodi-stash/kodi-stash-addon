
import random
import sys
from datetime import timedelta
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin
import xbmcgui
import xbmcplugin
import xbmc
import routing
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

SceneFragment = """
fragment Scene on Scene {
    id,
    title,
    details,
    rating,
    date,
    o_counter,
    paths {
        screenshot,
        stream
    },
    studio {
        name,
        image_path
    },
    tags {
        id,
        name,
        image_path
    },
    movies {
        movie {
            name
        }
    },
    performers {
        name,
        image_path
    },
    file {
        duration,
        width,
        height,
        audio_codec,
        video_codec
    },
    scene_markers {
        id
    },
    galleries {
        images {
            file {
                width,
                height
            }
            paths {
                image
            }
        }
    }
}

"""

GalleryFragment = """
fragment Gallery on Gallery {
    id,
    title,
    path,
    date,
    scenes {
        title
    },
    cover {
        paths {
            image
        }
    },
    studio {
        name
    },
    images {
        file {
            width,
            height
        }
        paths {
            image
        }
    }
}

"""

PerformerFragment = """
fragment Performer on Performer {
    id,
    name,
    image_path,
    scenes {
        galleries {
            title,
            images {
                file {
                    width,
                    height
                }
                paths {
                    image
                }
            }
        }
    }
}

"""


plugin = routing.Plugin()

stash_url = xbmcplugin.getSetting(plugin.handle, 'stash_url')
hide_unorganised = xbmcplugin.getSetting(plugin.handle, 'hide_unorganised') == 'true'
api_token = xbmcplugin.getSetting(plugin.handle, 'api_token')

xbmc.log(f'{sys.argv}, {plugin.handle}, {stash_url}, {hide_unorganised}', xbmc.LOGINFO)

if api_token:
    headers = {
        'ApiKey': api_token
    }
    transport = RequestsHTTPTransport(
        url=urljoin(stash_url, '/graphql'),
        headers=headers,
        use_json=True
    )
    xbmc.log(f'{plugin.handle} stash plugin Using API Token', xbmc.LOGINFO)
else:
    xbmc.log(f'{plugin.handle} stash plugin using standard transport', xbmc.LOGINFO)
    transport = RequestsHTTPTransport(urljoin(stash_url, '/graphql'))
    
client = Client(transport=transport, fetch_schema_from_transport=True)


def common_item_info(mediatype: str):
    return {
        'genre': 'Adult / Pornography',
        'mpaa': 'NC-17',
        'mediatype': mediatype
    }


def random_fanart_from_gallery(gallery: Dict):
    # landscape images work best
    def wide_images():
        for image in gallery['images']:
            aspect = image['file']['width'] / max(image['file']['height'], 1)

            if aspect >= 1:
                yield image

    images = list(wide_images())
    if len(images) == 0:
        images = gallery['images']  # fallback to portrait if no landscape images were found

    if len(images) == 0:
        return None

    # a pic midway through the gallery is usually more "interesting"
    #image = images[int(len(images) / 2)]

    image = random.choice(images)

    return image['paths']['image']


def scene_directory_item(scene, label_format='{title}') -> xbmcgui.ListItem:
    title = scene['title']
    screenshot_url = scene['paths']['screenshot']
    gallery_count = len(scene['galleries'])
    studio = scene['studio']

    item = xbmcgui.ListItem(label=label_format.format(**scene))

    item.setInfo('video', {
        'title': title,
        'premiered': scene['date'],
        'studio': studio['name'] if studio else None,
        'duration': scene['file']['duration'],
        'tag': [t['name'] for t in scene['tags']],
        'plot': scene['details'],
        'votes': f'{scene["o_counter"]} orgasms',
        #**common_item_info('video')
    })

    item.setCast([
        {
            'name': p['name'],
            'thumbnail': p['image_path']
        }
        for p in scene['performers']
    ])

    item.addStreamInfo('video', {
        'codec': scene['file']['video_codec'],
        'width': scene['file']['width'],
        'height': scene['file']['height']
    })

    item.addStreamInfo('audio', {
        'codec': scene['file']['audio_codec']
    })

    # use a gallery cover for the fanart (if available)
    fanart_url = screenshot_url
    if gallery_count > 0:
        fanart_url = random_fanart_from_gallery(random.choice(scene['galleries']))

    item.setArt({
        'thumb': screenshot_url,
        'fanart': fanart_url,
        'clearlogo': studio['image_path'] if studio else None
    })

    # item.addContextMenuItems([
    #     ('Scene Markers', 'RunScript()')
    # ])

    return item


def add_scene_directory_item(scene, leaf=False, **kwargs):
    stream_url = scene['paths']['stream']
    marker_count = len(scene['scene_markers'])
    gallery_count = len(scene['galleries'])

    item = scene_directory_item(scene, **kwargs)



    if not leaf:
        #and (marker_count > 0 or gallery_count > 0):
        xbmcplugin.addDirectoryItem(plugin.handle,
                                    plugin.url_for(scene_contents, scene_id=scene['id']),
                                    item,
                                    isFolder=True)

    else:
        item.setProperty('IsPlayable', 'true')

        xbmcplugin.addDirectoryItem(plugin.handle, stream_url, item)


def gallery_directory_item(gallery, label_format='{title}') -> xbmcgui.ListItem:
    def gallery_title():
        title = gallery['title']
        if title is not None:
            return title

        first_scene = next(iter(gallery['scenes']), None)
        discriminator = first_scene["title"] if first_scene else Path(gallery['path']).name
        return f'Untitled Gallery ({discriminator})'

    title = label_format.format(title=gallery_title())
    studio = gallery['studio']
    cover_image_url = gallery['cover']['paths']['image'] if gallery['cover'] is not None else None

    item = xbmcgui.ListItem(label=title)

    item.setInfo('folder', {
        'title': title,
        'studio': studio['name'] if studio else None,
        **common_item_info('folder')
    })

    item.setArt({
        'thumb': cover_image_url,
        'icon': cover_image_url,
        'poster': cover_image_url,
        'fanart': random_fanart_from_gallery(gallery) or cover_image_url,
    })

    return item


def add_gallery_directory_item(gallery, **kwargs):
    item = gallery_directory_item(gallery, **kwargs)

    xbmcplugin.addDirectoryItem(plugin.handle,
                                plugin.url_for(gallery_contents, gallery_id=gallery['id']),
                                item,
                                isFolder=True)


def performer_directory_item(performer, label_format='{name}'):
    name = performer['name']
    image_url = performer['image_path']

    item = xbmcgui.ListItem(label=label_format.format(**performer))

    item.setInfo('folder', {
        'title': name,
        **common_item_info('folder')
    })

    def random_gallery_fanart():
        galleries = [gallery for scene in performer['scenes'] for gallery in scene['galleries']]
        if len(galleries) == 0:
            return None

        gallery = random.choice(galleries)

        xbmc.log(f'Picked gallery {gallery["title"]} for {name}', xbmc.LOGINFO)

        return random_fanart_from_gallery(gallery)

    item.setArt({
        'thumb': image_url,
        'icon': image_url,
        'poster': image_url,
        'fanart': random_gallery_fanart() or image_url,
    })

    return item


def add_performer_directory_item(performer, **kwargs):
    item = performer_directory_item(performer, **kwargs)

    xbmcplugin.addDirectoryItem(plugin.handle,
                                plugin.url_for(performer_contents, performer_id=performer['id']),
                                item,
                                isFolder=True)


def tag_directory_item(tag, label_format='{name}'):
    item = xbmcgui.ListItem(label=label_format.format(**tag))

    item.setArt({
        'thumb': tag['image_path'],
        'icon': tag['image_path'],
        'fanart': tag['image_path'],
    })

    return item


def add_tag_directory_item(tag, **kwargs):
    item = tag_directory_item(tag, **kwargs)

    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(tag_contents, tag_id=tag['id']), item, isFolder=True)


@plugin.route('/scenes/<scene_id>')
def scene_contents(scene_id: str):
    query = gql(
        SceneFragment + GalleryFragment + PerformerFragment +
        """
            query FindScene($id: ID!) {
                scene: findScene(id: $id) {
                    ... Scene,
                    
                    galleries {
                        ... Gallery
                    }
                    
                    scene_markers {
                        title,
                        preview,
                        seconds,
                        scene {
                            paths {
                                stream
                            },
                            file {
                                duration
                            }
                        }
                    }
                    
                    performers {
                        ... Performer
                    }
                }
            }
    """
    )

    scene = client.execute(query, {
        'id': scene_id
    })['scene']

    xbmcplugin.setPluginCategory(plugin.handle, scene['title'])
    xbmcplugin.setContent(plugin.handle, 'files')

    scene_stream_url = scene['paths']['stream']
    markers = scene['scene_markers']
    galleries = scene['galleries']
    tags = scene['tags']
    performers = scene['performers']

    add_scene_directory_item(scene, leaf=True, label_format='[B]{title}[/B]')

    for marker in markers:
        title = marker['title']
        offset_seconds = timedelta(seconds=marker['seconds'])
        scene_duration = timedelta(seconds=marker['scene']['file']['duration'])

        offset_percent = (offset_seconds / scene_duration) * 100

        item = xbmcgui.ListItem(label=f'[I]Marker:[/I] [{offset_seconds}] {title}')
        item.setInfo('video', {})
        item.setProperty('IsPlayable', 'true')
        item.setProperty('StartPercent', str(offset_percent))

        xbmcplugin.addDirectoryItem(plugin.handle, scene_stream_url, item)

    for gallery in galleries:
        add_gallery_directory_item(gallery, label_format='[I]Gallery:[/I] {title}')

    for tag in tags:
        add_tag_directory_item(tag, label_format='[I]Tag:[/I] {name}')

    for performer in performers:
        add_performer_directory_item(performer, label_format='[I]Performer:[/I] {name}')


    xbmcplugin.endOfDirectory(plugin.handle)



@plugin.route('/scenes')
def list_scenes():
    query = gql(
        SceneFragment +
        """
            query ListScenes($organized: Boolean) {
                allScenes: findScenes(filter: {per_page: -1}, scene_filter: {organized: $organized}) {
                    scenes {
                        ... Scene
                    }
                }
            }
    """
    )

    scenes = client.execute(query, {
        'organized': hide_unorganised or None
    })['allScenes']['scenes']

    xbmcplugin.setPluginCategory(plugin.handle, 'Scenes')
    xbmcplugin.setContent(plugin.handle, 'videos')

    for scene in scenes:
        add_scene_directory_item(scene)

    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/movies/<movie_id>')
def movie_contents(movie_id: str):
    query = gql(
        SceneFragment +
        """
            query FindMovie($id: ID!) {
                movie: findMovie(id: $id) {
                    name
                },
                
                movieScenes: findScenes(scene_filter: {movies: {value: [$id], modifier: INCLUDES}}) {
                    scenes {
                        ... Scene
                    }
                },
            }
    """
    )

    result = client.execute(query, {
        'id': movie_id
    })

    movie = result['movie']
    scenes = result['movieScenes']['scenes']

    xbmcplugin.setPluginCategory(plugin.handle, movie['name'])
    xbmcplugin.setContent(plugin.handle, 'files')

    for scene in scenes:
        add_scene_directory_item(scene)

    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/movies')
def list_movies():
    query = gql(
        """
            query ListMovies {
                allMovies: findMovies(filter: {per_page: -1}) {
                    movies {
                        id,
                        name,
                        synopsis,
                        director,
                        front_image_path,
                        back_image_path,
                        date
                        studio {
                            name
                        },
                    }
                }
            }
    """
    )

    movies = client.execute(query)['allMovies']['movies']

    xbmcplugin.setPluginCategory(plugin.handle, 'Movies')
    xbmcplugin.setContent(plugin.handle, 'movies')

    for movie in movies:
        title = movie['name']
        studio = movie['studio']

        item = xbmcgui.ListItem(label=title)

        item.setInfo('video', {
            'title': title,
            'premiered': movie['date'],
            'studio': studio['name'] if studio else None,
            'plot': movie['synopsis'],
            'director': movie['director'],
            **common_item_info('folder')
        })

        item.setArt({
            'thumb': movie['front_image_path'],
            'icon': movie['front_image_path'],
            'poster': movie['front_image_path'],
            'back': movie['back_image_path'],
            'fanart': movie['front_image_path'],
        })

        xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(movie_contents, movie_id=movie['id']), item, isFolder=True)

    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/markers')
def list_markers():
    query = gql(
        """
            query ListMarkers {
                allMarkers: findSceneMarkers(filter: {per_page: -1}) {
                    scene_markers {
                        title,
                        seconds,
                        scene {
                            title,
                            paths {
                                stream
                            }
                        }
                        preview,
                        stream,
                        
                    }
                }
            }
    """
    )

    markers = client.execute(query)['allMarkers']['scene_markers']

    xbmcplugin.setPluginCategory(plugin.handle, 'Markers')
    xbmcplugin.setContent(plugin.handle, 'videos')

    for marker in markers:
        title = marker['title']

        item = xbmcgui.ListItem(label=title)

        item.setInfo('video', {
            'title': title,
            **common_item_info('video')
        })

        xbmc.log(marker['preview'], xbmc.LOGINFO)

        item.setArt({
            'thumb': marker['preview'],
            'icon': marker['preview'],
            'fanart': marker['preview'],
        })

        item.setProperty('IsPlayable', 'true')

        xbmcplugin.addDirectoryItem(plugin.handle, marker['stream'], item)

    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/performers/<performer_id>')
def performer_contents(performer_id: str):
    query = gql(
        SceneFragment + GalleryFragment +
        """
            query FindPerformer($id: ID!, $organized: Boolean) {
                performer: findPerformer(id: $id) {
                    id,
                    name,
                    image_path
                }
                
                performerScenes: findScenes(scene_filter: {performers: {value: [$id], modifier: INCLUDES}, organized: $organized}) {
                    scenes {
                        ... Scene
                    }
                }
                
                performerGalleries: findGalleries(gallery_filter: {performers: {value: [$id], modifier: INCLUDES}, organized: $organized}) {
                    galleries {
                        ... Gallery
                    }
                }
            }
    """
    )

    result = client.execute(query, {
        'id': performer_id,
        'organized': hide_unorganised or None
    })

    performer = result['performer']
    scenes = result['performerScenes']['scenes']
    galleries = result['performerGalleries']['galleries']

    xbmcplugin.setPluginCategory(plugin.handle, performer['name'])
    xbmcplugin.setContent(plugin.handle, 'files')

    for scene in scenes:
        add_scene_directory_item(scene, label_format='Scene: {title}')

    for gallery in galleries:
        add_gallery_directory_item(gallery, label_format='Gallery: {title}')


    xbmcplugin.endOfDirectory(plugin.handle)



@plugin.route('/performers')
def list_performers():
    query = gql(
        PerformerFragment +
        """
            query ListPerformers {
                allPerformers: findPerformers(filter: {per_page: -1}) {
                    performers {
                        ... Performer
                    }
                }
            }
    """
    )

    performers = client.execute(query)['allPerformers']['performers']

    xbmcplugin.setPluginCategory(plugin.handle, 'Performers')
    xbmcplugin.setContent(plugin.handle, 'artists')

    for performer in performers:
        add_performer_directory_item(performer)

    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/studios')
def list_studios():
    return


@plugin.route('/galleries/<gallery_id>')
def gallery_contents(gallery_id: str):
    query = gql(
        SceneFragment + PerformerFragment +
        """
            query FindGallery($id: ID!) {
                gallery: findGallery(id: $id) {
                    title,
                    images {
                        title,
                        file {
                            width,
                            height,
                            size
                        },
                        paths {
                            image
                        },
                        studio {
                            name
                        }
                    },
                    performers {
                        ... Performer
                    }
                    scenes {
                        ... Scene
                    }
                }
            }
    """
    )

    gallery = client.execute(query, {
        'id': gallery_id
    })['gallery']

    xbmcplugin.setPluginCategory(plugin.handle, gallery['title'])
    xbmcplugin.setContent(plugin.handle, 'images')

    images = gallery['images']
    scenes = gallery['scenes']
    performers = gallery['performers']

    for scene in scenes:
        add_scene_directory_item(scene, label_format='[I]Scene:[/I] {title}')

    for performer in performers:
        add_performer_directory_item(performer, label_format='[I]Performer:[/I] {name}')


    for image in images:
        title = image['title']

        item = xbmcgui.ListItem(label=title)

        item.setInfo('image', {
            'title': title,
            'url': image['paths']['image']
        })
        #
        item.setProperty('IsPlayable', 'true')

        xbmc.log(image['paths']['image'], xbmc.LOGINFO)

        item.setProperty('mimetype', 'image/jpeg')

        xbmcplugin.addDirectoryItem(plugin.handle, '', item)




    xbmcplugin.endOfDirectory(plugin.handle)

    # xbmc.executebuiltin("Container.SetViewMode(500)")

@plugin.route('/galleries')
def list_galleries():
    query = gql(
        GalleryFragment +
        """
            query ListGalleries($organized: Boolean) {
                allGalleries: findGalleries(filter: {per_page: -1}, gallery_filter: {organized: $organized}) {
                    galleries {
                        ... Gallery
                    }
                }
            }
    """
    )

    galleries = client.execute(query, {
        'organized': hide_unorganised or None
    })['allGalleries']['galleries']

    xbmcplugin.setPluginCategory(plugin.handle, 'Galleries')
    xbmcplugin.setContent(plugin.handle, 'files')

    for gallery in galleries:
        add_gallery_directory_item(gallery)

    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/tags/<tag_id>')
def tag_contents(tag_id: str):
    query = gql(
        SceneFragment + GalleryFragment +
        """
            query FindTag($id: ID!) {
                tag: findTag(id: $id) {
                    name
                },
                
                taggedScenes: findScenes(scene_filter: {tags: {value: [$id], modifier: INCLUDES}}) {
                    scenes {
                        ... Scene
                    }
                },
                
                taggedGalleries: findGalleries(gallery_filter: {tags: {value: [$id], modifier: INCLUDES}}) {
                    galleries {
                        ... Gallery
                    }
                },
                
                taggedMarkers: findSceneMarkers(scene_marker_filter: {tags: {value: [$id], modifier: INCLUDES}}) {
                    scene_markers {
                        id
                    }
                }
            }
    """
    )

    result = client.execute(query, {
        'id': tag_id
    })

    tag = result['tag']
    scenes = result['taggedScenes']['scenes']
    galleries = result['taggedGalleries']['galleries']

    xbmcplugin.setPluginCategory(plugin.handle, tag['name'])
    xbmcplugin.setContent(plugin.handle, 'files')

    for scene in scenes:
        add_scene_directory_item(scene, label_format='Scene: {title}')

    for gallery in galleries:
        add_gallery_directory_item(gallery, label_format='Gallery: {title}')

    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/tags')
def list_tags():
    query = gql(
        """
            query ListTags {
                allTags: findTags(filter: {per_page: -1}) {
                    tags {
                        id,
                        name
                        image_path
                    }
                }
            }
    """
    )

    tags = client.execute(query)['allTags']['tags']

    xbmcplugin.setPluginCategory(plugin.handle, 'Tags')
    xbmcplugin.setContent(plugin.handle, 'files')

    for tag in tags:
        add_tag_directory_item(tag)

    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route('/')
def list_root_items():
    xbmcplugin.setPluginCategory(plugin.handle, 'Stash')
    xbmcplugin.setContent(plugin.handle, 'files')

    items = [
        ('Scenes', plugin.url_for(list_scenes)),
        ('Movies', plugin.url_for(list_movies)),
        # ('Markers', plugin.url_for(list_markers)),
        ('Performers', plugin.url_for(list_performers)),
        # ('Studios', plugin.url_for(list_studios)),
        ('Galleries', plugin.url_for(list_galleries)),
        ('Tags', plugin.url_for(list_tags))
    ]

    for group in items:
        item = xbmcgui.ListItem(label=group[0])

        url = group[1]
        xbmcplugin.addDirectoryItem(plugin.handle, url, item, isFolder=True)

    xbmcplugin.endOfDirectory(plugin.handle)




if __name__ == '__main__':
    plugin.run()
