class CreateGenes < ActiveRecord::Migration
  def change
    create_table :genes do |t|
      t.string :name
      t.string :description, limit: 1000
      t.references :organism
      t.string :ortholog_name
      t.string :ortholog_description, :ortholog_species, limit: 1000
      t.integer :ortholog_length, :ortholog_sw_score
      t.float :ortholog_identity, precision: 4, scale: 3
    end
  end
end
