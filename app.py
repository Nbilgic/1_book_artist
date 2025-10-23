# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler


from forms import *
from flask_migrate import Migrate

from models import Venue, Show, Artist, db

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
# db = SQLAlchemy(app)
migrate = Migrate(app, db)

db.init_app(app)



# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    venues = Venue.query.all()
    data = []

    # Helper dict to group venues by city-state
    city_state_map = {}

    for venue in venues:
        # Count upcoming shows for this venue
        num_upcoming_shows = Show.query.filter(
            Show.venue_id == venue.id,
            Show.start_time > datetime.now()
        ).count()

        # Create venue dict
        venue_data = {
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": num_upcoming_shows
        }

        # Group by city-state
        key = (venue.city, venue.state)
        if key not in city_state_map:
            city_state_map[key] = {
                "city": venue.city,
                "state": venue.state,
                "venues": []
            }
        city_state_map[key]["venues"].append(venue_data)

    # Convert grouped dict to list
    data = list(city_state_map.values())

    return render_template('pages/venues.html', areas=data);


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # search for Hop should return "The Musical Hop".
    # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"

    filtered_venues = Venue.query.filter(Venue.name.ilike(f"%{request.form.get('search_term', '')}%")).all()
    data = []
    for venue in filtered_venues:
        data.append({"id": venue.id, "name": venue.name, "num_upcoming_shows": 0})  # Placeholder for num_upcoming_shows

    response = {
        "count": len(filtered_venues),
        "data": data
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id

    venue = Venue.query.get_or_404(venue_id)  # get venue or return 404
    past_shows = []
    upcoming_shows = []

    # Query shows for this venue
    shows = Show.query.filter_by(venue_id=venue_id).join(Artist).all()

    for show in shows:
        show_info = {
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }
        if show.start_time < datetime.now():
            past_shows.append(show_info)
        else:
            upcoming_shows.append(show_info)

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": getattr(venue, 'genres', []),
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": getattr(venue, 'website', ''),
        "facebook_link": venue.facebook_link,
        "seeking_talent": getattr(venue, 'seeking_talent', False),
        "seeking_description": getattr(venue, 'seeking_description', ''),
        "image_link": getattr(venue, 'image_link', ''),
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    try:
        venue = Venue(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            address=form.address.data,
            phone=form.phone.data,
            genres=form.genres.data,
            image_link=form.image_link.data,
            facebook_link=form.facebook_link.data,
            website=form.website_link.data,
            seeking_talent=form.seeking_talent.data,
            seeking_description=form.seeking_description.data
        )
        db.session.add(venue)
        db.session.commit()

        # on successful db insert, flash success
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        db.session.rollback()
        print(f"Error occurred: {e}")
        # flash an error message
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()

    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        if not venue:
            return jsonify({
                'success': False,
                'message': f'Venue with ID {venue_id} not found.'
            }), 404

        db.session.delete(venue)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Venue "{venue.name}" was successfully deleted.'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'An error occurred while deleting the venue: {str(e)}'
        }), 500

    finally:
        db.session.close()


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    artists = Artist.query.all()
    data = []
    for artist in artists:
        data.append({
            "id": artist.id,
            "name": artist.name
        })
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".
    artists = Artist.query.filter(Artist.name.ilike(f"%{request.form.get('search_term', '')}%")).all()
    data = []
    for artist in artists:
        num_of_upcoming_shows = Show.query.filter(Show.artist_id == artist.id, Show.start_time > datetime.now()).count()
        data.append({"id": artist.id, "name": artist.name, "num_upcoming_shows": num_of_upcoming_shows})

    response = {
        "count": len(artists),
        "data": data
    }
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = Artist.query.get_or_404(artist_id)
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)

    # Prepopulate the form with existing artist data
    form = ArtistForm(obj=artist)

    artist = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": getattr(artist, 'website', ''),
        "facebook_link": getattr(artist, 'facebook_link', ''),
        "seeking_venue": getattr(artist, 'seeking_venue', False),
        "seeking_description": getattr(artist, 'seeking_description', ''),
        "image_link": getattr(artist, 'image_link', '')
    }

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # Get the existing artist from DB
    form = ArtistForm(request.form)
    artist = Artist.query.get_or_404(artist_id)


    try:
        # Update artist attributes from form data
        artist.name = request.form['name']
        artist.city = request.form['city']
        artist.state = request.form['state']
        artist.phone = request.form['phone']
        artist.image_link = request.form['image_link']
        artist.facebook_link = request.form['facebook_link']
        artist.website = request.form.get('website_link', '')
        artist.genres = request.form.getlist('genres')
        artist.seeking_venue = 'seeking_venue' in request.form
        artist.seeking_description = request.form.get('seeking_description', '')


        # Commit the changes
        db.session.commit()
        flash(f'Artist "{artist.name}" was successfully updated!')

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating artist {artist_id}: {e}")
        flash(f'An error occurred. Artist "{artist.name}" could not be updated.')

    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get_or_404(venue_id)
    # Populate the form with existing venue data
    form.name.data = venue.name
    form.city.data = venue.city
    form.state.data = venue.state
    form.address.data = venue.address
    form.phone.data = venue.phone
    form.genres.data = venue.genres
    form.image_link.data = venue.image_link
    form.facebook_link.data = venue.facebook_link
    form.website_link.data = venue.website if hasattr(venue, 'website') else ''
    form.seeking_talent.data = venue.seeking_talent if hasattr(venue, 'seeking_talent') else False
    form.seeking_description.data = venue.seeking_description if hasattr(venue, 'seeking_description') else ''

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue:
        flash(f'Venue with ID {venue_id} not found.')
        return redirect(url_for('index'))

    try:
        # Get form data
        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.address = request.form['address']
        venue.phone = request.form['phone']
        venue.image_link = request.form['image_link']
        venue.facebook_link = request.form['facebook_link']
        venue.website = request.form.get('website_link')
        venue.genres = request.form.getlist('genres')
        venue.seeking_talent = True if 'seeking_talent' in request.form else False
        venue.seeking_description = request.form.get('seeking_description', '')

        # Commit the changes
        db.session.commit()
        flash(f'Venue "{venue.name}" was successfully updated!')

    except Exception as e:
        db.session.rollback()
        print(e)
        flash(f'An error occurred. Venue "{venue.name}" could not be updated.')

    finally:
        db.session.close()

    # venue record with ID <venue_id> using the new attributes
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form

    try:
        artist = Artist(
            name=request.form['name'],
            city=request.form['city'],
            state=request.form['state'],
            phone=request.form['phone'],
            genres=request.form.getlist('genres'),
            image_link=request.form['image_link'],
            facebook_link=request.form['facebook_link'],
        )
        db.session.add(artist)
        db.session.commit()
        # on successful db insert, flash success
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        db.session.rollback()
        print(f"Error occurred: {e}")
        # flash an error message
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    data = []
    shows = Show.query.join(Venue).join(Artist).all()
    for show in shows:
        data.append({
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        })
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    try:
        show = Show(
            artist_id=request.form['artist_id'],
            venue_id=request.form['venue_id'],
            start_time=request.form['start_time']
        )
        db.session.add(show)
        db.session.commit()
        # on successful db insert, flash success
        flash('Show was successfully listed!')
    except Exception as e:
        db.session.rollback()
        print(f"Error occurred: {e}")
        # flash an error message
        flash('An error occurred. Show could not be listed.')
    finally:
        db.session.close()
    # e.g., flash('An error occurred. Show could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
