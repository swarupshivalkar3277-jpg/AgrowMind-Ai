const categories = ["Fertilizers", "Seeds", "Trees/Saplings", "Pesticides", "Farming Tools"];

export default function MarketplaceCarousel() {
  return (
    <div className="categoryCarousel">
      {categories.map((category) => <span key={category}>{category}</span>)}
    </div>
  );
}
