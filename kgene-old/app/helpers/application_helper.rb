module ApplicationHelper
  # Hash of items for top navigation links
  # Each key has an array of link, [matching controller symbols]
  def top_navbar_items
    {
      explore: [root_path,[:home]],
      organisms: [organisms_path,[:organisms]],
      process_organism: [processes_path,[:processes]]
    }
  end
  # return top nav bar html
  # set the active class for any items matching the controller name
  def application_top_navbar_items
    content_tag( :ul, id: "top-navigation", class: "nav navbar-nav") do
      top_navbar_items.collect{ |k,v|
        content_tag :li, link_to(k.to_s.titleize,v[0]), class: ('active' if v[1].find{|key| params[:controller] =~ /#{key}/} )
      }.join.html_safe + ''
      #((current_user && current_user.is_admin?) ? content_tag(:li, link_to("Admin", admin_root_path, class: ('active' if params[:controller]=~/^admin/))) : '')
    end
  end
end
