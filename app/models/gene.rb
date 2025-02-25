require 'csv'
require 'nokogiri'
require 'open-uri'
class Gene < ActiveRecord::Base
  validates :name, presence: true
  
  belongs_to :organism
  
  def self.fetch_and_store_from_org(organism)
    begin
      resource = RestClient::Resource.new "http://rest.kegg.jp/list/#{organism.code}"
      resource.get.split("\n").each do |line|
        line.gsub!(/\"/,"\'")
        data = line.parse_csv({col_sep: "\t"})
        Gene.create(name: data[0], description: data[1], organism_id: organism.id)
      end
    rescue => e
      organism.update_attributes(job_error: e, status: 'error')
    else
      organism.update_attributes(job_error: nil)
    ensure
      organism.update_attributes(status: 'pending')
    end
  end
  
  def self.fetch_and_store_orthologs_for_organism(organism)
    exclude_item = organism.name.split(/ /)[0..1].join(' ')
    orgs = Organism.hash_of
    begin
      Parallel.each(organism.genes, in_threads: 10) do |gene|
        ActiveRecord::Base.connection_pool.with_connection do
          doc = Nokogiri::HTML(open("https://www.kegg.jp/ssdb-bin/ssdb_best_best?org_gene=#{gene.name}&sort_by=sw_sp"))
          table = doc.at('pre').text.to_s
          
          species = nil
          non_matching_ortholog = table.split("\n")[2..-1].find{ |line|
            (entry,definition) = line[0..54].split("\s")
            org_code = entry.split(':').first
            species = orgs[org_code]
          
            species !~ /#{exclude_item}/
          }
          if non_matching_ortholog
            (entry,definition) = non_matching_ortholog[0..54].split("\s")
            org_code = entry.split(':').first
            species = orgs[org_code]
            len = non_matching_ortholog[63..69].strip
            sw_score = non_matching_ortholog[70..79].strip
            identity = non_matching_ortholog[98..107].strip
          
            gene.update_attributes(
              ortholog_name: entry,
              ortholog_description: definition,
              ortholog_species: species,
              ortholog_length: len,
              ortholog_sw_score: sw_score,
              ortholog_identity: identity
            )
          else
            gene.update_attributes(
              ortholog_description: 'N/A',
              ortholog_species: 'N/A',
            )
          end
          
          doc = nil
          table = nil
          non_matching_ortholog = nil
        end
      end
    rescue => e
      Rails.logger.error e
      Rails.logger.error e.backtrace.join("\n")
      organism.update_attributes(job_error: e, status: 'error')
    else
      organism.update_attributes(job_error: nil)
    ensure
      organism.update_attributes(status: 'complete')
    end
  end
end
