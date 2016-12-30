from django.views import generic

from .models import Lineup

class IndexView(generic.ListView):
    template_name = 'lineups/index.html'
    context_object_name = 'lineup_list'

    def get_queryset(self):
        """Return the last ten lineups."""
        return Lineup.objects.order_by('-updated')[:10]


class DetailView(generic.DetailView):
    model = Lineup
    template_name = 'lineups/detail.html'
