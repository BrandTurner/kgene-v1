class Organism < ActiveRecord::Base
  validates :code, :name, presence: true
  validates :code, uniqueness: true
  
  has_many :genes
  
  scope :jobs, -> { where.not(status: nil) }
  scope :active_jobs, -> { where(status: 'pending') }
  
  def active_job?
    self.status == 'pending'
  end
  
  def self.hash_of
    hash = {}
    Organism.all.each do |o|
      hash[o.code] = o.name
    end
    return hash
  end
  
  def perc_complete
    if genes.empty?
      return 0
    else
      (genes.where.not(ortholog_name: nil).count.to_f / genes.count.to_f) * 100.0
    end
  end
end
